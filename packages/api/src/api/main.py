from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.domain.models.job import Job
from core.domain.models.schemas import (
    JobStubCreate,
    JobDetailUpdate,
    RefinementResult,
    ClaimRequest,
    KnownUrlsRequest,
    DetectionResult,
    TranslationResult,
)
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
)
from api.config import get_database_url, get_api_secret

app = FastAPI(title="Job Sourcing API", version="1.0.0")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


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


@app.get("/status")
@limiter.limit("120/minute")
async def health_status(
    request: Request, usecase: GetDatabaseStatusUseCase = Depends(get_status_usecase)
):
    return usecase.execute()


@app.post("/jobs/known-urls", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def check_known_urls(
    request: Request,
    body: KnownUrlsRequest,
    usecase: CheckKnownUrlsUseCase = Depends(get_check_known_urls_usecase),
):
    known = usecase.execute(body.urls)
    return {"known_urls": list(known)}


@app.post("/jobs", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def create_jobs(
    request: Request,
    stubs: list[JobStubCreate],
    usecase: CreateJobsUseCase = Depends(get_create_jobs_usecase),
):
    inserted_count = usecase.execute(stubs)
    return {"inserted": inserted_count}


@app.get("/jobs/pending-details", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def get_pending_details(
    request: Request,
    source: Optional[str] = None,
    usecase: GetPendingDetailsUseCase = Depends(get_pending_details_usecase),
):
    jobs = usecase.execute(source=source)
    return [j.to_dict() for j in jobs]


@app.put("/jobs/details", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def update_job_details(
    request: Request,
    details: list[JobDetailUpdate],
    usecase: UpdateJobDetailsUseCase = Depends(get_update_details_usecase),
):
    usecase.execute(details)
    return {"updated": len(details)}


@app.post("/jobs/claim-detect", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def claim_detection_job(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimDetectionJobUseCase = Depends(get_detect_claim_usecase),
):
    job = usecase.execute(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/detect", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_detection(
    request: Request,
    result: DetectionResult,
    usecase: CompleteDetectionUseCase = Depends(get_detect_complete_usecase),
):
    usecase.execute(
        url=result.url,
        language_code=result.language_code,
    )
    return {"status": "completed", "url": result.url}


@app.post("/jobs/claim-translate", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def claim_translation_job(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimTranslationJobUseCase = Depends(get_translate_claim_usecase),
):
    job = usecase.execute(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/translate", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_translation(
    request: Request,
    result: TranslationResult,
    usecase: CompleteTranslationUseCase = Depends(get_translate_complete_usecase),
):
    usecase.execute(
        url=result.url,
        description_en=result.description_en,
        requirements_en=result.requirements_en,
    )
    return {"status": "completed", "url": result.url}


@app.post("/jobs/claim-refine", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def claim_refinement_job(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimRefinementJobUseCase = Depends(get_refine_claim_usecase),
):
    job = usecase.execute(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/refine", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_refinement(
    request: Request,
    result: RefinementResult,
    usecase: CompleteRefinementUseCase = Depends(get_refine_complete_usecase),
):
    usecase.execute(
        url=result.url,
        required_skills=result.required_skills,
        education_level=result.education_level,
        city=result.city,
        country=result.country,
    )
    return {"status": "completed", "url": result.url}
