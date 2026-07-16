from core.domain.interfaces.db import BaseStatusQueryRepository

class GetDatabaseStatusUseCase:
    def __init__(self, repo: BaseStatusQueryRepository):
        self._repo = repo

    def execute(self) -> dict:
        return self._repo.get_status()
