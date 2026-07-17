from typing import Optional
from core.domain.interfaces.db import BaseCandidateProfileRepository
from core.domain.models.profile import CandidateProfile
from core.services.cv_extractor import CvExtractor


class IngestCandidateProfileUseCase:
    def __init__(
        self,
        repo: BaseCandidateProfileRepository,
        extractor: Optional[CvExtractor] = None,
    ):
        self._repo = repo
        self._extractor = extractor or CvExtractor()

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

        # Save to database
        saved_profile = self._repo.save(profile)
        return saved_profile


class GetCandidateProfileUseCase:
    def __init__(self, repo: BaseCandidateProfileRepository):
        self._repo = repo

    def execute(self, profile_id: int) -> Optional[CandidateProfile]:
        return self._repo.get_by_id(profile_id)
