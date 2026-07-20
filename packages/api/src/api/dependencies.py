from fastapi import Depends, HTTPException, Header
from core.domain.interfaces.services import BaseStorageService
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
    ClaimIngestionUseCase,
    CompleteIngestionUseCase,
    FailIngestionUseCase,
    SubmitRawTextUseCase,
    ClaimProfileDetectionUseCase,
    CompleteProfileDetectionUseCase,
    ClaimProfileTranslationUseCase,
    CompleteProfileTranslationUseCase,
    ClaimProfileRefinementUseCase,
    CompleteProfileRefinementUseCase,
    ClaimMatchingTaskUseCase,
    SubmitTaskMatchesUseCase,
    FailMatchingTaskUseCase,
    GetCandidateMatchesUseCase,
    ClaimMatchExplanationUseCase,
    CompleteMatchExplanationUseCase,
    FailMatchExplanationUseCase,
)
from api.config import get_database_url, get_api_secret, get_match_threshold

_repo: PipelineJobRepository | None = None
_storage_service: BaseStorageService | None = None


def get_storage_service() -> BaseStorageService:
    global _storage_service
    if _storage_service is None:
        from core.infrastructure.services.storage import get_storage_service_from_env

        _storage_service = get_storage_service_from_env()
    return _storage_service


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
    return CompleteRefinementUseCase(repo.refinement, repo.matching_queue)


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


async def verify_token(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    expected = f"Bearer {get_api_secret()}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_ingest_profile_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
    storage: BaseStorageService = Depends(get_storage_service),
) -> IngestCandidateProfileUseCase:
    return IngestCandidateProfileUseCase(
        repo.profiles,
        storage,
    )


def get_candidate_profile_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> GetCandidateProfileUseCase:
    return GetCandidateProfileUseCase(repo.profiles)


def get_claim_matching_task_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimMatchingTaskUseCase:
    return ClaimMatchingTaskUseCase(repo.matching_queue)


def get_submit_task_matches_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> SubmitTaskMatchesUseCase:
    return SubmitTaskMatchesUseCase(repo.matching_queue, repo.matches)


def get_fail_matching_task_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailMatchingTaskUseCase:
    return FailMatchingTaskUseCase(repo.matching_queue)


def get_candidate_matches_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> GetCandidateMatchesUseCase:
    return GetCandidateMatchesUseCase(repo.matches)


def get_claim_match_explanation_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimMatchExplanationUseCase:
    return ClaimMatchExplanationUseCase(repo.matches, threshold=get_match_threshold())


def get_complete_match_explanation_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteMatchExplanationUseCase:
    return CompleteMatchExplanationUseCase(repo.matches)


def get_fail_match_explanation_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailMatchExplanationUseCase:
    return FailMatchExplanationUseCase(repo.matches)


def get_list_profiles_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
):
    from core.usecases.profiles import ListCandidateProfilesUseCase

    return ListCandidateProfilesUseCase(repo.profiles)


def get_refined_jobs_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
):
    from core.usecases.jobs import GetRefinedJobsUseCase

    return GetRefinedJobsUseCase(repo)


def get_recent_urls_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
):
    from core.usecases.jobs import GetRecentUrlsUseCase

    return GetRecentUrlsUseCase(repo)


def get_crawler_checkpoint_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
):
    from core.usecases.jobs import GetCrawlerCheckpointUseCase

    return GetCrawlerCheckpointUseCase(repo)


def update_crawler_checkpoint_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
):
    from core.usecases.jobs import UpdateCrawlerCheckpointUseCase

    return UpdateCrawlerCheckpointUseCase(repo)


def get_claim_ingestion_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimIngestionUseCase:
    return ClaimIngestionUseCase(repo.profiles)


def get_complete_ingestion_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteIngestionUseCase:
    return CompleteIngestionUseCase(repo.profiles, repo.matching_queue)


def get_fail_ingestion_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> FailIngestionUseCase:
    return FailIngestionUseCase(repo.profiles)


def get_submit_raw_text_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> SubmitRawTextUseCase:
    return SubmitRawTextUseCase(repo.profiles)


def get_claim_profile_detect_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimProfileDetectionUseCase:
    return ClaimProfileDetectionUseCase(repo.profiles)


def get_complete_profile_detect_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteProfileDetectionUseCase:
    return CompleteProfileDetectionUseCase(repo.profiles)


def get_claim_profile_translate_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimProfileTranslationUseCase:
    return ClaimProfileTranslationUseCase(repo.profiles)


def get_complete_profile_translate_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteProfileTranslationUseCase:
    return CompleteProfileTranslationUseCase(repo.profiles)


def get_claim_profile_refine_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> ClaimProfileRefinementUseCase:
    return ClaimProfileRefinementUseCase(repo.profiles)


def get_complete_profile_refine_usecase(
    repo: PipelineJobRepository = Depends(get_repo),
) -> CompleteProfileRefinementUseCase:
    return CompleteProfileRefinementUseCase(repo.profiles, repo.matching_queue)
