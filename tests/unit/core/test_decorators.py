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
    assert result is False


@patch("requests.post")
def test_send_telegram_message_success(mock_post, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
    mock_post.return_value.status_code = 200

    result = send_telegram_message(12345, "Hello")
    assert result is True
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
