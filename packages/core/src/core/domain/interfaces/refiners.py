from abc import ABC, abstractmethod
from core.domain.models.schemas import RefinementResult

class BaseRefiner(ABC):
    @abstractmethod
    def refine(
        self,
        url: str,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> RefinementResult:
        pass
