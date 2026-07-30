from core.domain.interfaces.db import BaseJobRepository
from core.domain.models.schemas import JobDetailUpdate


class UpdateJobDetailsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, details: list[JobDetailUpdate]) -> None:
        self._repo.update_details(details)
