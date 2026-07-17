from fastapi import APIRouter, Depends, Request
from core.domain.models.schemas import ClaimRequest, TranslationResult
from api.dependencies import (
    get_translate_claim_usecase,
    ClaimTranslationJobUseCase,
    get_translate_complete_usecase,
    CompleteTranslationUseCase,
    verify_token,
)
from api.limiter_config import limiter

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/jobs/claim-translate")
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


@router.put("/jobs/translate")
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
