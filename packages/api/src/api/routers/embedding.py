from core.domain.models.schemas import (
    ClaimRequest,
    EmbeddingJobResult,
    ProfileEmbeddingResult,
)
from core.utils.decorators import notify_telegram_on_cv_completion
from fastapi import APIRouter, Depends, Request

from api.dependencies import (
    ClaimEmbeddingJobUseCase,
    ClaimProfileEmbeddingUseCase,
    CompleteEmbeddingJobUseCase,
    CompleteProfileEmbeddingUseCase,
    get_claim_profile_embed_usecase,
    get_complete_profile_embed_usecase,
    get_embed_claim_usecase,
    get_embed_complete_usecase,
    verify_token,
)
from api.limiter_config import limiter

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs/claim-embed")
@limiter.limit("60/minute")
async def claim_embedding_job(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimEmbeddingJobUseCase = Depends(get_embed_claim_usecase),
):
    job = usecase.execute(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending embedding jobs available"}
    return {"job": job.to_dict()}


@router.put("/jobs/embed")
@limiter.limit("60/minute")
async def submit_job_embedding(
    request: Request,
    result: EmbeddingJobResult,
    usecase: CompleteEmbeddingJobUseCase = Depends(get_embed_complete_usecase),
):
    usecase.execute(
        url=result.url,
        skill_embedding=result.skill_embedding,
        research_embedding=result.research_embedding,
        degree_embedding=result.degree_embedding,
    )
    return {"status": "completed", "url": result.url}


@router.post("/profiles/claim-embed")
@limiter.limit("60/minute")
async def claim_profile_embed(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimProfileEmbeddingUseCase = Depends(get_claim_profile_embed_usecase),
):
    profile = usecase.execute(body.agent_name)
    if profile is None:
        return {
            "profile": None,
            "message": "No pending profile embedding tasks available",
        }
    return {"profile": profile.to_dict()}


@router.put("/profiles/complete-embed")
@limiter.limit("60/minute")
@notify_telegram_on_cv_completion
async def complete_profile_embed(
    request: Request,
    body: ProfileEmbeddingResult,
    usecase: CompleteProfileEmbeddingUseCase = Depends(get_complete_profile_embed_usecase),
):
    final_id = usecase.execute(
        profile_id=body.profile_id,
        skill_embedding=body.skill_embedding,
        research_embedding=body.research_embedding,
        degree_embedding=body.degree_embedding,
    )
    return {"status": "success", "profile_id": final_id}
