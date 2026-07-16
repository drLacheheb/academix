from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.schemas import RefinementResult


class BaseRefiner(ABC):

    @abstractmethod
    def refine(self, url: str, title: str, description: str | None, requirements: str | None) -> RefinementResult:
        ...
