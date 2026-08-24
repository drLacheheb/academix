from core.domain.interfaces.db import BaseJobRepository
from core.domain.models.job import Job


class GetRefinedJobsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self) -> list[Job]:
        return self._repo.get_refined_jobs()


class GetRecentUrlsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, source: str, limit: int = 500) -> list[str]:
        return self._repo.get_recent_urls(source, limit)
