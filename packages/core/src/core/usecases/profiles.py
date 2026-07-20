from typing import Optional
from core.domain.interfaces.db import (
    BaseCandidateProfileRepository,
    BaseMatchingQueueRepository,
)
from core.domain.models.profile import CandidateProfile
from core.domain.interfaces.services import BaseStorageService


class IngestCandidateProfileUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        storage_service: BaseStorageService,
    ):
        self._repo = repo
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
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
    ):
        self._repo = repo

    def execute(self, profile_id: int, profile: CandidateProfile) -> None:
        self._repo.complete_ingestion(profile_id, profile)


class FailIngestionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int, error_message: str) -> None:
        self._repo.fail_ingestion(profile_id, error_message)


class SubmitRawTextUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(
        self,
        profile_id: int,
        raw_text: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        self._repo.submit_raw_text(profile_id, raw_text, name, email)


class ClaimProfileDetectionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Optional[CandidateProfile]:
        from datetime import datetime, timedelta
        from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES

        cutoff = datetime.now() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next_for_detection(agent_name, cutoff)


class CompleteProfileDetectionUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int, language_code: str) -> None:
        self._repo.complete_detection(profile_id, language_code)


class ClaimProfileTranslationUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Optional[CandidateProfile]:
        from datetime import datetime, timedelta
        from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES

        cutoff = datetime.now() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next_for_translation(agent_name, cutoff)


class CompleteProfileTranslationUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int, raw_text_en: str) -> None:
        self._repo.complete_translation(profile_id, raw_text_en)


class ClaimProfileRefinementUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, agent_name: str) -> Optional[CandidateProfile]:
        from datetime import datetime, timedelta
        from core.domain.constants import STALE_CLAIM_TIMEOUT_MINUTES

        cutoff = datetime.now() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
        return self._repo.claim_next_for_refinement(agent_name, cutoff)


class CompleteProfileRefinementUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        queue_repo: BaseMatchingQueueRepository,
    ):
        self._repo = repo
        self._queue_repo = queue_repo

    def execute(self, profile_id: int, profile: CandidateProfile) -> None:
        self._repo.complete_refinement(profile_id, profile)
        # Enqueue the profile ID for matching task
        self._queue_repo.enqueue("candidate", str(profile_id))
