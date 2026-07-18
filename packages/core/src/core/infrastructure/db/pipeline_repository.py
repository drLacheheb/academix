from datetime import datetime, timedelta, timezone

from core.domain.interfaces.db import BaseStatusQueryRepository
from core.domain.models.job import Job
from core.domain.constants import (
    STALE_CLAIM_TIMEOUT_MINUTES,
)
from core.domain.interfaces.services import BaseEmbeddingService
from core.infrastructure.db.repository import DatabaseJobRepository
from core.infrastructure.db.detection import LanguageDetectionRepository
from core.infrastructure.db.translation import TranslationRepository
from core.infrastructure.db.refinement import RefinementRepository
from core.infrastructure.db.status import StatusQueryRepository
from core.infrastructure.db.profile_repository import DatabaseCandidateProfileRepository
from core.infrastructure.db.matching_queue import MatchingQueueRepository
from core.infrastructure.db.match_repository import MatchRepository


class PipelineJobRepository(DatabaseJobRepository, BaseStatusQueryRepository):
    def __init__(self, database_url: str, embedding_service: BaseEmbeddingService):
        super().__init__(database_url)
        self.detection = LanguageDetectionRepository(self._SessionLocal)
        self.translation = TranslationRepository(self._SessionLocal)
        self.refinement = RefinementRepository(self._SessionLocal, embedding_service=embedding_service)
        self.status = StatusQueryRepository(self._SessionLocal)
        self.profiles = DatabaseCandidateProfileRepository(self._SessionLocal)
        self.matching_queue = MatchingQueueRepository(self._SessionLocal)
        self.matches = MatchRepository(self._SessionLocal)

    def claim_next_for_detection(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self.detection.claim_next(agent_name, cutoff)

    def complete_detection(self, url: str, language_code: str) -> None:
        return self.detection.complete(url, language_code)

    def fail_detection(self, url: str) -> None:
        return self.detection.fail(url)

    def claim_next_for_translation(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self.translation.claim_next(agent_name, cutoff)

    def complete_translation(
        self,
        url: str,
        description_en: str | None,
        requirements_en: str | None,
    ) -> None:
        return self.translation.complete(url, description_en, requirements_en)

    def fail_translation(self, url: str) -> None:
        return self.translation.fail(url)

    def claim_next_for_refinement(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self.refinement.claim_next(agent_name, cutoff)

    def complete_refinement(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        return self.refinement.complete(
            url, required_skills, education_level, city, country
        )

    def fail_refinement(self, url: str) -> None:
        return self.refinement.fail(url)

    def _recover_stale_claims(self, session) -> int:
        stale_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        recovered = 0
        recovered += self.detection.recover_stale(stale_cutoff)
        recovered += self.translation.recover_stale(stale_cutoff)
        recovered += self.refinement.recover_stale(stale_cutoff)
        recovered += self.matching_queue.recover_stale(stale_cutoff)
        recovered += self.matches.recover_stale_explanations(stale_cutoff)
        return recovered

    def get_status(self) -> dict:
        return self.status.get_status()
