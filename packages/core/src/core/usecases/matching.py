from datetime import datetime, timezone, timedelta
from typing import Optional
from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import BaseMatchingQueueRepository, BaseMatchRepository
from core.domain.models.match import Match
from core.domain.models.matching_task import MatchingTask


class ClaimMatchingTaskUseCase:
    def __init__(self, queue_repo: BaseMatchingQueueRepository):
        self._queue_repo = queue_repo

    def execute(self, agent_name: str) -> Optional[MatchingTask]:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._queue_repo.claim_next(agent_name, cutoff)


class SubmitTaskMatchesUseCase:
    def __init__(self, queue_repo: BaseMatchingQueueRepository, match_repo: BaseMatchRepository):
        self._queue_repo = queue_repo
        self._match_repo = match_repo

    def execute(self, task_id: int, matches: list[Match]) -> None:
        self._match_repo.save_matches(matches)
        self._queue_repo.complete(task_id)


class FailMatchingTaskUseCase:
    def __init__(self, queue_repo: BaseMatchingQueueRepository):
        self._queue_repo = queue_repo

    def execute(self, task_id: int) -> None:
        self._queue_repo.fail(task_id)


class GetCandidateMatchesUseCase:
    def __init__(self, match_repo: BaseMatchRepository):
        self._match_repo = match_repo

    def execute(self, candidate_id: int, limit: int = 20) -> list[Match]:
        return self._match_repo.get_matches_for_candidate(candidate_id, limit)


class ClaimMatchExplanationUseCase:
    def __init__(self, match_repo: BaseMatchRepository, threshold: float = 0.3):
        self._match_repo = match_repo
        self._threshold = threshold

    def execute(self, agent_name: str) -> Optional[Match]:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._match_repo.claim_next_pending_explanation(agent_name, cutoff, self._threshold)


class CompleteMatchExplanationUseCase:
    def __init__(self, match_repo: BaseMatchRepository):
        self._match_repo = match_repo

    def execute(self, match_id: int, explanation: str) -> None:
        self._match_repo.complete_explanation(match_id, explanation)


class FailMatchExplanationUseCase:
    def __init__(self, match_repo: BaseMatchRepository):
        self._match_repo = match_repo

    def execute(self, match_id: int) -> None:
        self._match_repo.fail_explanation(match_id)
