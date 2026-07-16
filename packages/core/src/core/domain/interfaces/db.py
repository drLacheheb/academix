from abc import ABC, abstractmethod
from datetime import datetime
from core.domain.models.job import Job
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
    def complete(self, url: str, description_en: str | None, requirements_en: str | None) -> None:
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
