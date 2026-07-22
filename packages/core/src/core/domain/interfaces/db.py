from abc import ABC, abstractmethod
from datetime import datetime
from core.domain.models.job import Job
from core.domain.models.profile import CandidateProfile
from core.domain.models.match import Match
from core.domain.models.matching_task import MatchingTask
from core.domain.models.schemas import JobDetailUpdate


class BaseJobRepository(ABC):
    @abstractmethod
    def init_db(self) -> None:
        pass

    @abstractmethod
    def update_details(self, details: list[JobDetailUpdate]) -> None:
        pass

    @abstractmethod
    def load(self) -> list[Job]:
        pass

    @abstractmethod
    def save(self, jobs: list[Job]) -> None:
        pass

    @abstractmethod
    def get_known_urls(self, urls: list[str]) -> set[str]:
        pass

    @abstractmethod
    def get_unstored(self, source: str | None = None) -> list[Job]:
        pass

    @abstractmethod
    def get_refined_jobs(self) -> list[Job]:
        pass

    @abstractmethod
    def get_recent_urls(self, source: str, limit: int = 500) -> list[str]:
        pass

    @abstractmethod
    def get_crawler_checkpoint(self, source: str) -> str | None:
        pass

    @abstractmethod
    def update_crawler_checkpoint(self, source: str, url: str) -> None:
        pass


class BaseDetectionRepository(ABC):
    @abstractmethod
    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        pass

    @abstractmethod
    def complete(self, url: str, language_code: str) -> None:
        pass

    @abstractmethod
    def fail(self, url: str) -> None:
        pass

    @abstractmethod
    def recover_stale(self, stale_cutoff: datetime) -> int:
        pass


class BaseTranslationRepository(ABC):
    @abstractmethod
    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        pass

    @abstractmethod
    def complete(
        self, url: str, description_en: str | None, requirements_en: str | None
    ) -> None:
        pass

    @abstractmethod
    def fail(self, url: str) -> None:
        pass

    @abstractmethod
    def recover_stale(self, stale_cutoff: datetime) -> int:
        pass


class BaseRefinementRepository(ABC):
    @abstractmethod
    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        pass

    @abstractmethod
    def complete(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    def fail(self, url: str) -> None:
        pass

    @abstractmethod
    def recover_stale(self, stale_cutoff: datetime) -> int:
        pass


class BaseStatusQueryRepository(ABC):
    @abstractmethod
    def get_status(self) -> dict:
        pass


class BaseCandidateProfileRepository(ABC):
    @abstractmethod
    def save(self, profile: CandidateProfile) -> CandidateProfile:
        pass

    @abstractmethod
    def get_by_id(self, profile_id: int) -> CandidateProfile | None:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> CandidateProfile | None:
        pass

    @abstractmethod
    def get_all(self) -> list[CandidateProfile]:
        pass

    @abstractmethod
    def claim_next_for_ingestion(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        pass

    @abstractmethod
    def complete_ingestion(self, profile_id: int, profile: CandidateProfile) -> None:
        pass

    @abstractmethod
    def fail_ingestion(self, profile_id: int, error_message: str) -> None:
        pass

    @abstractmethod
    def submit_raw_text(
        self,
        profile_id: int,
        raw_text: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    def claim_next_for_detection(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        pass

    @abstractmethod
    def complete_detection(self, profile_id: int, language_code: str) -> None:
        pass

    @abstractmethod
    def claim_next_for_translation(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        pass

    @abstractmethod
    def complete_translation(self, profile_id: int, raw_text_en: str) -> None:
        pass

    @abstractmethod
    def claim_next_for_refinement(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        pass

    @abstractmethod
    def complete_refinement(self, profile_id: int, profile: CandidateProfile) -> int:
        pass


class BaseMatchingQueueRepository(ABC):
    @abstractmethod
    def enqueue(self, entity_type: str, entity_id: str) -> None:
        pass

    @abstractmethod
    def claim_next(
        self, agent_name: str, stale_cutoff: datetime
    ) -> MatchingTask | None:
        pass

    @abstractmethod
    def complete(self, task_id: int) -> None:
        pass

    @abstractmethod
    def fail(self, task_id: int) -> None:
        pass

    @abstractmethod
    def recover_stale(self, stale_cutoff: datetime) -> int:
        pass


class BaseMatchRepository(ABC):
    @abstractmethod
    def save_matches(self, matches: list[Match]) -> None:
        pass

    @abstractmethod
    def get_matches_for_candidate(
        self, candidate_id: int, limit: int = 20
    ) -> list[Match]:
        pass

    @abstractmethod
    def exists(self, candidate_id: int, job_url: str) -> bool:
        pass

    @abstractmethod
    def claim_next_pending_explanation(
        self, agent_name: str, stale_cutoff: datetime, threshold: float = 0.3
    ) -> Match | None:
        pass

    @abstractmethod
    def complete_explanation(self, match_id: int, explanation: str) -> None:
        pass

    @abstractmethod
    def fail_explanation(self, match_id: int) -> None:
        pass

    @abstractmethod
    def recover_stale_explanations(self, stale_cutoff: datetime) -> int:
        pass
