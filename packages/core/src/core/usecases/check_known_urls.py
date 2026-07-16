from core.domain.interfaces.db import BaseJobRepository


class CheckKnownUrlsUseCase:
    def __init__(self, repo: BaseJobRepository):
        self._repo = repo

    def execute(self, urls: list[str]) -> set[str]:
        return self._repo.get_known_urls(urls)
