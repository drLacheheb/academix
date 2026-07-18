from typing import Optional
from core.domain.interfaces.db import BaseCandidateProfileRepository, BaseMatchingQueueRepository
from core.domain.models.profile import CandidateProfile
from core.domain.interfaces.services import BaseCvExtractor, BaseEmbeddingService, BaseStorageService


class IngestCandidateProfileUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        queue_repo: BaseMatchingQueueRepository,
        extractor: BaseCvExtractor,
        embedding_service: BaseEmbeddingService,
        storage_service: BaseStorageService,
    ):
        self._repo = repo
        self._queue_repo = queue_repo
        self._extractor = extractor
        self._embedding_service = embedding_service
        self._storage_service = storage_service

    def execute(
        self,
        file_name: str,
        file_content: bytes,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CandidateProfile:
        # Upload the CV file using our storage abstraction layer
        url_or_path = self._storage_service.upload(file_name, file_content)

        # Create a placeholder profile stub
        profile = CandidateProfile(
            name=name,
            email=email,
            cv_file_path=url_or_path,
            status="INGESTING",
            status_message="CV Uploaded. Ingestion task registered.",
        )

        # Save placeholder record to database
        saved_profile = self._repo.save(profile)
        return saved_profile


class GetCandidateProfileUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int) -> Optional[CandidateProfile]:
        return self._repo.get_by_id(profile_id)


class ListCandidateProfilesUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self) -> list[CandidateProfile]:
        return self._repo.get_all()


class ClaimIngestionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Optional[CandidateProfile]:
        from datetime import datetime, timedelta
        from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES
        cutoff = datetime.now() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next_for_ingestion(agent_name, cutoff)


class CompleteIngestionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository, queue_repo: BaseMatchingQueueRepository):
        self._repo = repo
        self._queue_repo = queue_repo

    def execute(self, profile_id: int, profile: CandidateProfile) -> None:
        self._repo.complete_ingestion(profile_id, profile)
        # Enqueue the profile ID for matching task
        self._queue_repo.enqueue("candidate", str(profile_id))


class FailIngestionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int, error_message: str) -> None:
        self._repo.fail_ingestion(profile_id, error_message)
