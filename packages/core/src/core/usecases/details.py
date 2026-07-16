from core.domain.models.schemas import JobDetailUpdate
from core.domain.interfaces.db import BaseJobRepository


class UpdateJobDetailsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, details: list[JobDetailUpdate]) -> None:
        self._repo.update_details(details)
