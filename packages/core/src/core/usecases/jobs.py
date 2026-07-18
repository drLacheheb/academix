from core.domain.interfaces.db import BaseJobRepository
from core.domain.models.job import Job


class GetRefinedJobsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self) -> list[Job]:
        return self._repo.get_refined_jobs()
