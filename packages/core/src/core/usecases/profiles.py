from typing import Optional
from core.domain.interfaces.db import BaseCandidateProfileRepository, BaseMatchingQueueRepository
from core.domain.models.profile import CandidateProfile
from core.domain.interfaces.services import BaseCvExtractor, BaseEmbeddingService


class IngestCandidateProfileUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        queue_repo: BaseMatchingQueueRepository,
        extractor: BaseCvExtractor,
        embedding_service: BaseEmbeddingService,
    ):
        self._repo = repo
        self._queue_repo = queue_repo
        self._extractor = extractor
        self._embedding_service = embedding_service

    def execute(
        self,
        file_path: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CandidateProfile:
        # Extract profile from CV
        profile, raw_text = self._extractor.extract_profile(file_path)

        # Apply overrides if provided
        if email:
            profile.email = email
        if name:
            profile.name = name

        profile.cv_file_path = file_path

        # Validate that we have a valid email identifier
        if not profile.email or profile.email == "None":
            raise ValueError(
                "Could not extract email address from the CV. Please provide it explicitly in the request form."
            )

        # Compute semantic embeddings for skills and research interests
        profile.skill_embedding = self._embedding_service.encode_skills(profile.skills)
        profile.research_embedding = self._embedding_service.encode_research(profile.research_interests)

        # Save to database
        saved_profile = self._repo.save(profile)

        # Enqueue matching task
        self._queue_repo.enqueue("candidate", str(saved_profile.id))

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
