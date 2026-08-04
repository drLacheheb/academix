from datetime import UTC, datetime, timedelta

from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
from core.domain.interfaces.db import (
    BaseCandidateProfileRepository,
    BaseEmbeddingRepository,
    BaseMatchingQueueRepository,
)
from core.domain.models.job import Job
from core.domain.models.profile import CandidateProfile


class ClaimEmbeddingJobUseCase:
    def __init__(self, repo: BaseEmbeddingRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Job | None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        return self._repo.claim_next(agent_name, cutoff)


class CompleteEmbeddingJobUseCase:
    def __init__(self, repo: BaseEmbeddingRepository, queue_repo: BaseMatchingQueueRepository):
        self._repo = repo
        self._queue_repo = queue_repo

    def execute(
        self,
        url: str,
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        degree_embedding: list[float] | None = None,
    ) -> None:
        self._repo.complete(url, skill_embedding, research_embedding, degree_embedding)
        self._queue_repo.enqueue("job", url)


class FailEmbeddingJobUseCase:
    def __init__(self, repo: BaseEmbeddingRepository):
        self._repo = repo

    def execute(self, url: str) -> None:
        self._repo.fail(url)


class ClaimProfileEmbeddingUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> CandidateProfile | None:
        cutoff = datetime.now() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next_for_embedding(agent_name, cutoff)


class CompleteProfileEmbeddingUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        queue_repo: BaseMatchingQueueRepository,
    ):
        self._repo = repo
        self._queue_repo = queue_repo

    def execute(
        self,
        profile_id: int,
        skill_embedding: list[float] | None,
        research_embedding: list[float] | None,
        degree_embedding: list[float] | None,
    ) -> int:
        self._repo.complete_embedding(
            profile_id, skill_embedding, research_embedding, degree_embedding
        )
        self._queue_repo.enqueue("candidate", str(profile_id))
        return profile_id
