from abc import ABC, abstractmethod
from core.domain.models.job import Job
from core.domain.models.schemas import JobDetailUpdate

class BaseDiscovery(ABC):
    SOURCE_NAME: str = ""

    @abstractmethod
    def search_all(self, known_urls: set[str]) -> list[Job]:
        pass

    @abstractmethod
    def _build_browse_url(self, page: int) -> str:
        pass

    @abstractmethod
    def _parse_search_page(self, html_content: str) -> list[Job]:
        pass


class BaseSourcing(ABC):
    SOURCE_NAME: str = ""

    @abstractmethod
    def source_detail(self, url: str) -> JobDetailUpdate:
        pass

    @abstractmethod
    def _parse_detail_page(self, html_content: str, url: str) -> JobDetailUpdate:
        pass
