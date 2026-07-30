from datetime import UTC, datetime, timedelta

from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import BaseTranslationRepository
from core.domain.models.job import Job


class ClaimTranslationJobUseCase:
    def __init__(self, repo: BaseTranslationRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self._repo.claim_next(agent_name, cutoff)


class CompleteTranslationUseCase:
    def __init__(self, repo: BaseTranslationRepository):
        self._repo = repo

    def execute(self, url: str, description_en: str | None, requirements_en: str | None) -> None:
        self._repo.complete(url, description_en, requirements_en)


class FailTranslationUseCase:
    def __init__(self, repo: BaseTranslationRepository):
        self._repo = repo

    def execute(self, url: str) -> None:
        self._repo.fail(url)
