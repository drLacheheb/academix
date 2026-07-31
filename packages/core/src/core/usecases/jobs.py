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

    def execute(self, source: str, limit: int = 500) -> tuple[list[str], int]:
        urls = self._repo.get_recent_urls(source, limit)
        total_count = self._repo.get_total_count(source)
        return urls, total_count


class GetTotalCountUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, source: str) -> int:
        return self._repo.get_total_count(source)


class GetCrawlerCheckpointUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, source: str) -> str | None:
        return self._repo.get_crawler_checkpoint(source)


class UpdateCrawlerCheckpointUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, source: str, url: str) -> None:
        self._repo.update_crawler_checkpoint(source, url)
