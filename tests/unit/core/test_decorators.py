from unittest.mock import MagicMock, patch

import pytest
from core.utils.decorators import (
    notify_telegram_on_cv_completion,
    notify_telegram_on_matches_found,
    send_telegram_message,
)


def test_send_telegram_message_no_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    result = send_telegram_message(12345, "Hello")
    assert bool(result) is False
    assert result.success is False


@patch("requests.post")
def test_send_telegram_message_success(mock_post, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
    mock_post.return_value.status_code = 200

    result = send_telegram_message(12345, "Hello")
    assert bool(result) is True
    assert result.success is True
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["chat_id"] == 12345
    assert payload["text"] == "Hello"


@pytest.mark.asyncio
async def test_notify_telegram_on_cv_completion_with_profile():
    with patch("core.utils.decorators.send_telegram_message") as mock_send:
        mock_send.return_value = True

        @notify_telegram_on_cv_completion
        async def dummy_endpoint():
            return {
                "profile": {
                    "id": 1,
                    "name": "Jane Doe",
                    "telegram_chat_id": "555123",
                    "highest_degree": "PhD",
                    "degree_fields": ["Computer Science"],
                    "skills": ["Python", "FastAPI"],
                    "research_interests": ["Machine Learning"],
                }
            }

        result = await dummy_endpoint()
        assert result["profile"]["name"] == "Jane Doe"
        mock_send.assert_called_once()
        chat_id, msg = mock_send.call_args[0]
        assert chat_id == "555123"
        assert "Jane Doe" in msg
        assert "CV Processing Complete!" in msg


@pytest.mark.asyncio
async def test_notify_telegram_on_matches_found_with_direct_matches():
    with (
        patch("core.utils.decorators.send_telegram_message") as mock_send,
        patch("core.infrastructure.db.pipeline_repository.PipelineJobRepository") as mock_repo_cls,
    ):
        mock_send.return_value = True
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        @notify_telegram_on_matches_found
        async def dummy_match_endpoint():
            return {
                "matches": [
                    {
                        "match_id": 101,
                        "candidate_id": 1,
                        "telegram_chat_id": "555123",
                        "job_url": "https://example.com/job-1",
                        "score": 0.88,
                        "job_title": "Postdoctoral Researcher in AI",
                        "employer": "University of Amsterdam",
                        "city": "Amsterdam",
                        "country": "Netherlands",
                        "deadline": "2026-10-01",
                        "degree_fields": ["Computer Science"],
                        "explanation": "High research alignment.",
                    }
                ]
            }

        result = await dummy_match_endpoint()
        assert len(result["matches"]) == 1
        mock_send.assert_called_once()
        chat_id, msg = mock_send.call_args[0]
        assert chat_id == "555123"
        assert "Postdoctoral Researcher in AI" in msg
        assert "88% Match" in msg
        mock_repo.matches.mark_as_notified.assert_called_once_with([101])


@pytest.mark.asyncio
async def test_notify_telegram_on_matches_found_permanent_failure_marks_notified():
    from core.utils.decorators import TelegramSendResult

    with (
        patch("core.utils.decorators.send_telegram_message") as mock_send,
        patch("core.infrastructure.db.pipeline_repository.PipelineJobRepository") as mock_repo_cls,
    ):
        mock_send.return_value = TelegramSendResult(
            success=False,
            status_code=403,
            error_message="Forbidden: bot was blocked by the user",
        )
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        @notify_telegram_on_matches_found
        async def dummy_blocked_match_endpoint():
            return {
                "matches": [
                    {
                        "match_id": 202,
                        "candidate_id": 2,
                        "telegram_chat_id": "blocked_user_1877",
                        "job_url": "https://example.com/job-blocked",
                        "score": 0.85,
                        "job_title": "PhD Position",
                        "employer": "ETH Zurich",
                    }
                ]
            }

        result = await dummy_blocked_match_endpoint()
        assert len(result["matches"]) == 1
        # Permanent failure (403) must mark match as notified to break infinite loops
        mock_repo.matches.mark_as_notified.assert_called_once_with([202])


@pytest.mark.asyncio
async def test_notify_telegram_on_matches_found_transient_failure_keeps_unnotified():
    from core.utils.decorators import TelegramSendResult

    with (
        patch("core.utils.decorators.send_telegram_message") as mock_send,
        patch("core.infrastructure.db.pipeline_repository.PipelineJobRepository") as mock_repo_cls,
    ):
        mock_send.return_value = TelegramSendResult(
            success=False,
            status_code=500,
            error_message="Internal Server Error",
        )
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        @notify_telegram_on_matches_found
        async def dummy_transient_match_endpoint():
            return {
                "matches": [
                    {
                        "match_id": 303,
                        "candidate_id": 3,
                        "telegram_chat_id": "user_303",
                        "job_url": "https://example.com/job-transient",
                        "score": 0.90,
                        "job_title": "Postdoc Position",
                    }
                ]
            }

        result = await dummy_transient_match_endpoint()
        assert len(result["matches"]) == 1
        # Transient failure (500) should NOT mark match as notified so it can be retried later
        mock_repo.matches.mark_as_notified.assert_not_called()


@patch("requests.post")
def test_send_telegram_message_caches_blocked_user(mock_post, monkeypatch):
    import core.utils.decorators as dec

    dec._BLOCKED_CHAT_IDS.clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")

    # First attempt: Telegram returns 403 Forbidden
    mock_post.return_value.status_code = 403
    mock_post.return_value.text = (
        '{"ok":false,"description":"Forbidden: bot was blocked by the user"}'
    )

    res1 = dec.send_telegram_message("blocked_999", "Hello 1")
    assert bool(res1) is False
    assert res1.is_permanent_failure is True
    assert mock_post.call_count == 1

    # Second attempt: Should use cached blocked status and NOT make an HTTP request
    res2 = dec.send_telegram_message("blocked_999", "Hello 2")
    assert bool(res2) is False
    assert res2.is_permanent_failure is True
    assert mock_post.call_count == 1  # count did not increase


def test_unblock_chat_clears_cache():
    import core.utils.decorators as dec

    dec._BLOCKED_CHAT_IDS.clear()
    dec._mark_chat_blocked("user_777")
    assert dec._is_chat_blocked("user_777") is True

    dec.unblock_chat("user_777")
    assert dec._is_chat_blocked("user_777") is False
