from fastapi import APIRouter, Depends, Request
from core.domain.models.schemas import ClaimRequest, DetectionResult
from api.dependencies import (
    get_detect_claim_usecase,
    ClaimDetectionJobUseCase,
    get_detect_complete_usecase,
    CompleteDetectionUseCase,
    verify_token,
)
from api.limiter_config import limiter

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs/claim-detect")
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


@router.put("/jobs/detect")
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
