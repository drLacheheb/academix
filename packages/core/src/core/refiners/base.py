from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.job import Job


class BaseRefiner(ABC):

    @abstractmethod
    def refine(self, job: Job) -> Job:
        ...
