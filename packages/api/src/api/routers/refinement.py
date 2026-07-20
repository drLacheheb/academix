from fastapi import APIRouter, Depends, Request
from core.domain.models.schemas import ClaimRequest, RefinementResult
from api.dependencies import (
    get_refine_claim_usecase,
    ClaimRefinementJobUseCase,
    get_refine_complete_usecase,
    CompleteRefinementUseCase,
    verify_token,
)
from api.limiter_config import limiter

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs/claim-refine")
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


@router.put("/jobs/refine")
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
        skill_embedding=result.skill_embedding,
        research_embedding=result.research_embedding,
        city=result.city,
        country=result.country,
    )
    return {"status": "completed", "url": result.url}
