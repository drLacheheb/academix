from datetime import UTC, datetime, timedelta

from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import BaseDetectionRepository
from core.domain.models.job import Job


class ClaimDetectionJobUseCase:
    def __init__(self, repo: BaseDetectionRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self._repo.claim_next(agent_name, cutoff)


class CompleteDetectionUseCase:
    def __init__(self, repo: BaseDetectionRepository):
        self._repo = repo

    def execute(self, url: str, language_code: str) -> None:
        self._repo.complete(url, language_code)


class FailDetectionUseCase:
    def __init__(self, repo: BaseDetectionRepository):
        self._repo = repo

    def execute(self, url: str) -> None:
        self._repo.fail(url)
