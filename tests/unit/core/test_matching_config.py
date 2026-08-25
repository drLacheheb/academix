from unittest.mock import MagicMock

from core.domain.models.match import Match
from core.infrastructure.db.match_repository import MatchRepository
from core.infrastructure.db.models import MatchModel


def test_save_matches_with_explanation_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_MATCH_EXPLANATION", "false")

    mock_session = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.query.return_value.filter.return_value.first.return_value = None

    repo = MatchRepository(mock_session_factory)
    matches = [
        Match(
            candidate_id=1,
            job_url="https://example.com/job-1",
            score=0.88,
            degree_eligible=True,
            language_eligible=True,
            skill_score=0.9,
            research_score=0.85,
        )
    ]

    repo.save_matches(matches)

    # Check model added to session
    added_model = mock_session.add.call_args[0][0]
    assert isinstance(added_model, MatchModel)
    assert added_model.explanation_status == "skipped"


def test_save_matches_with_explanation_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_MATCH_EXPLANATION", "true")

    mock_session = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.query.return_value.filter.return_value.first.return_value = None

    repo = MatchRepository(mock_session_factory)
    matches = [
        Match(
            candidate_id=1,
            job_url="https://example.com/job-1",
            score=0.88,
            degree_eligible=True,
            language_eligible=True,
            skill_score=0.9,
            research_score=0.85,
        )
    ]

    repo.save_matches(matches)

    added_model = mock_session.add.call_args[0][0]
    assert isinstance(added_model, MatchModel)
    assert added_model.explanation_status == "pending"
