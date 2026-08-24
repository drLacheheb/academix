from datetime import UTC, datetime, timedelta

from core.domain.constants import (
    STALE_CLAIM_TIMEOUT_MINUTES,
)
from core.domain.interfaces.db import BaseStatusQueryRepository
from core.domain.models.job import Job
from core.infrastructure.db.embedding import EmbeddingRepository
from core.infrastructure.db.match_repository import MatchRepository
from core.infrastructure.db.matching_queue import MatchingQueueRepository
from core.infrastructure.db.profile_repository import DatabaseCandidateProfileRepository
from core.infrastructure.db.refinement import RefinementRepository
from core.infrastructure.db.repository import DatabaseJobRepository
from core.infrastructure.db.status import StatusQueryRepository
from core.infrastructure.db.translation import TranslationRepository


class PipelineJobRepository(DatabaseJobRepository, BaseStatusQueryRepository):
    def __init__(self, database_url: str):
        super().__init__(database_url)
        self.translation = TranslationRepository(self._SessionLocal)
        self.refinement = RefinementRepository(self._SessionLocal)
        self.embedding = EmbeddingRepository(self._SessionLocal)
        self.status = StatusQueryRepository(self._SessionLocal)
        self.profiles = DatabaseCandidateProfileRepository(self._SessionLocal)
        self.matching_queue = MatchingQueueRepository(self._SessionLocal)
        self.matches = MatchRepository(self._SessionLocal)

    def claim_next_for_translation(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self.translation.claim_next(agent_name, cutoff)

    def complete_translation(
        self,
        url: str,
        job_details_en: str | None = None,
    ) -> None:
        return self.translation.complete(url, job_details_en)

    def fail_translation(self, url: str) -> None:
        return self.translation.fail(url)

    def claim_next_for_refinement(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self.refinement.claim_next(agent_name, cutoff)

    def complete_refinement(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None = None,
        degree_fields: list[str] | None = None,
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        city: str | None = None,
        country: str | None = None,
        employer: str | None = None,
        deadline: str | None = None,
    ) -> None:
        return self.refinement.complete(
            url=url,
            required_skills=required_skills,
            education_level=education_level,
            degree_fields=degree_fields or [],
            skill_embedding=skill_embedding,
            research_embedding=research_embedding,
            city=city,
            country=country,
            employer=employer,
            deadline=deadline,
        )

    def fail_refinement(self, url: str) -> None:
        return self.refinement.fail(url)

    def claim_next_for_embedding(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self.embedding.claim_next(agent_name, cutoff)

    def complete_embedding(
        self,
        url: str,
        skill_embedding: list[float],
        research_embedding: list[float],
        degree_embedding: list[float] | None = None,
    ) -> None:
        return self.embedding.complete(url, skill_embedding, research_embedding, degree_embedding)

    def fail_embedding(self, url: str) -> None:
        return self.embedding.fail(url)

    def get_status(self) -> dict:
        return self.status.get_status()

    def recover_stale_claims(self) -> int:
        stale_cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        recovered = 0
        recovered += self.translation.recover_stale(stale_cutoff)
        recovered += self.refinement.recover_stale(stale_cutoff)
        recovered += self.embedding.recover_stale(stale_cutoff)
        recovered += self.matching_queue.recover_stale(stale_cutoff)
        return recovered
