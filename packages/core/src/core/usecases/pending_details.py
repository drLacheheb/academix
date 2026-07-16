from core.domain.models.job import Job
from core.domain.interfaces.db import BaseJobRepository


class GetPendingDetailsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, source: str | None = None) -> list[Job]:
        return self._repo.get_unstored(source=source)
