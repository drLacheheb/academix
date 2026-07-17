from fastapi import Depends, HTTPException, Header
from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from core.usecases import (
    ClaimDetectionJobUseCase,
    CompleteDetectionUseCase,
    FailDetectionUseCase,
    ClaimTranslationJobUseCase,
    CompleteTranslationUseCase,
    FailTranslationUseCase,
    ClaimRefinementJobUseCase,
    CompleteRefinementUseCase,
    FailRefinementUseCase,
    GetDatabaseStatusUseCase,
    UpdateJobDetailsUseCase,
    CheckKnownUrlsUseCase,
    CreateJobsUseCase,
    GetPendingDetailsUseCase,
    IngestCandidateProfileUseCase,
    GetCandidateProfileUseCase,
)
from api.config import get_database_url, get_api_secret

_repo: PipelineJobRepository | None = None


def get_repo() -> PipelineJobRepository:
    global _repo
    if _repo is None:
        _repo = PipelineJobRepository(get_database_url())
    return _repo


# Dependency providers for Use Cases
def get_detect_claim_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimDetectionJobUseCase:
    return ClaimDetectionJobUseCase(repo.detection)


def get_detect_complete_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteDetectionUseCase:
    return CompleteDetectionUseCase(repo.detection)


def get_detect_fail_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailDetectionUseCase:
    return FailDetectionUseCase(repo.detection)


def get_translate_claim_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimTranslationJobUseCase:
    return ClaimTranslationJobUseCase(repo.translation)


def get_translate_complete_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteTranslationUseCase:
    return CompleteTranslationUseCase(repo.translation)


def get_translate_fail_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailTranslationUseCase:
    return FailTranslationUseCase(repo.translation)


def get_refine_claim_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimRefinementJobUseCase:
    return ClaimRefinementJobUseCase(repo.refinement)


def get_refine_complete_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteRefinementUseCase:
    return CompleteRefinementUseCase(repo.refinement)


def get_refine_fail_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailRefinementUseCase:
    return FailRefinementUseCase(repo.refinement)


def get_status_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> GetDatabaseStatusUseCase:
    return GetDatabaseStatusUseCase(repo.status)


def get_update_details_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> UpdateJobDetailsUseCase:
    return UpdateJobDetailsUseCase(repo)


def get_check_known_urls_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CheckKnownUrlsUseCase:
    return CheckKnownUrlsUseCase(repo)


def get_create_jobs_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CreateJobsUseCase:
    return CreateJobsUseCase(repo)


def get_pending_details_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> GetPendingDetailsUseCase:
    return GetPendingDetailsUseCase(repo)


async def verify_token(authorization: str = Header(...)):
    expected = f"Bearer {get_api_secret()}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_ingest_profile_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> IngestCandidateProfileUseCase:
    return IngestCandidateProfileUseCase(repo.profiles)


def get_candidate_profile_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> GetCandidateProfileUseCase:
    return GetCandidateProfileUseCase(repo.profiles)

