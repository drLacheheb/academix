from typing import Optional
from fastapi import APIRouter, Depends, Request
from core.domain.models.schemas import (
    KnownUrlsRequest,
    JobStubCreate,
    JobDetailUpdate,
    CheckpointUpdate,
)
from api.dependencies import (
    get_check_known_urls_usecase,
    CheckKnownUrlsUseCase,
    get_create_jobs_usecase,
    CreateJobsUseCase,
    get_pending_details_usecase,
    GetPendingDetailsUseCase,
    get_update_details_usecase,
    UpdateJobDetailsUseCase,
    get_refined_jobs_usecase,
    get_recent_urls_usecase,
    get_crawler_checkpoint_usecase,
    update_crawler_checkpoint_usecase,
    verify_token,
)
from api.limiter_config import limiter

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs/known-urls")
@limiter.limit("30/minute")
async def check_known_urls(
    request: Request,
    body: KnownUrlsRequest,
    usecase: CheckKnownUrlsUseCase = Depends(get_check_known_urls_usecase),
):
    known = usecase.execute(body.urls)
    return {"known_urls": list(known)}


@router.post("/jobs")
@limiter.limit("30/minute")
async def create_jobs(
    request: Request,
    stubs: list[JobStubCreate],
    usecase: CreateJobsUseCase = Depends(get_create_jobs_usecase),
):
    inserted_count = usecase.execute(stubs)
    return {"inserted": inserted_count}


@router.get("/jobs/pending-details")
@limiter.limit("30/minute")
async def get_pending_details(
    request: Request,
    source: Optional[str] = None,
    usecase: GetPendingDetailsUseCase = Depends(get_pending_details_usecase),
):
    jobs = usecase.execute(source=source)
    return [j.to_dict() for j in jobs]


@router.put("/jobs/details")
@limiter.limit("30/minute")
async def update_job_details(
    request: Request,
    details: list[JobDetailUpdate],
    usecase: UpdateJobDetailsUseCase = Depends(get_update_details_usecase),
):
    usecase.execute(details)
    return {"updated": len(details)}


@router.get("/jobs/refined")
@limiter.limit("60/minute")
async def get_refined_jobs(
    request: Request,
    usecase = Depends(get_refined_jobs_usecase),
):
    jobs = usecase.execute()
    return [j.to_dict() for j in jobs]


@router.get("/jobs/urls")
@limiter.limit("60/minute")
async def get_recent_urls(
    request: Request,
    source: str,
    limit: int = 500,
    usecase = Depends(get_recent_urls_usecase),
):
    urls = usecase.execute(source=source, limit=limit)
    return {"urls": urls}


@router.get("/jobs/checkpoint")
@limiter.limit("60/minute")
async def get_crawler_checkpoint(
    request: Request,
    source: str,
    usecase = Depends(get_crawler_checkpoint_usecase),
):
    val = usecase.execute(source=source)
    return {"checkpoint_url": val}


@router.put("/jobs/checkpoint")
@limiter.limit("30/minute")
async def update_crawler_checkpoint(
    request: Request,
    body: CheckpointUpdate,
    usecase = Depends(update_crawler_checkpoint_usecase),
):
    usecase.execute(source=body.source, url=body.url)
    return {"status": "updated", "source": body.source}
