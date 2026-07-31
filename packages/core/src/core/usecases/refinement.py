from datetime import UTC, datetime, timedelta

from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import (
    BaseRefinementRepository,
)
from core.domain.models.job import Job


class ClaimRefinementJobUseCase:
    def __init__(self, repo: BaseRefinementRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self._repo.claim_next(agent_name, cutoff)


class CompleteRefinementUseCase:
    def __init__(self, repo: BaseRefinementRepository):
        self._repo = repo

    def execute(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        self._repo.complete(
            url,
            required_skills,
            education_level,
            skill_embedding,
            research_embedding,
            city,
            country,
        )


class FailRefinementUseCase:
    def __init__(self, repo: BaseRefinementRepository):
        self._repo = repo

    def execute(self, url: str) -> None:
        self._repo.fail(url)
