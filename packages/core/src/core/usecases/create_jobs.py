from core.domain.models.job import Job
from core.domain.models.schemas import JobStubCreate
from core.domain.interfaces.db import BaseJobRepository


class CreateJobsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, stubs: list[JobStubCreate]) -> int:
        jobs = [
            Job(title=s.title, url=s.url, source=s.source)
            for s in stubs
        ]
        self._repo.save(jobs)
        return len(jobs)
