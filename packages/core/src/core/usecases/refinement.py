from datetime import datetime, timedelta, timezone
from core.domain.models.job import Job
from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import BaseRefinementRepository, BaseMatchingQueueRepository

class ClaimRefinementJobUseCase:
    def __init__(self, repo: BaseRefinementRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next(agent_name, cutoff)


class CompleteRefinementUseCase:
    def __init__(self, repo: BaseRefinementRepository, queue_repo: BaseMatchingQueueRepository):
        self._repo = repo
        self._queue_repo = queue_repo

    def execute(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        self._repo.complete(url, required_skills, education_level, city, country)
        self._queue_repo.enqueue("job", url)


class FailRefinementUseCase:
    def __init__(self, repo: BaseRefinementRepository):
        self._repo = repo

    def execute(self, url: str) -> None:
        self._repo.fail(url)
