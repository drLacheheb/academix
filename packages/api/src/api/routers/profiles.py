import os

from core.domain.models.schemas import ClaimRequest
from core.infrastructure.logging.logger import get_logger
from core.usecases import (
    ClaimIngestionUseCase,
    ClaimProfileDetectionUseCase,
    ClaimProfileRefinementUseCase,
    ClaimProfileTranslationUseCase,
    CompleteIngestionUseCase,
    CompleteProfileDetectionUseCase,
    CompleteProfileRefinementUseCase,
    CompleteProfileTranslationUseCase,
    FailIngestionUseCase,
    GetCandidateProfileUseCase,
    IngestCandidateProfileUseCase,
    SubmitRawTextUseCase,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from api.dependencies import (
    get_candidate_profile_usecase,
    get_claim_ingestion_usecase,
    get_claim_profile_detect_usecase,
    get_claim_profile_refine_usecase,
    get_claim_profile_translate_usecase,
    get_complete_ingestion_usecase,
    get_complete_profile_detect_usecase,
    get_complete_profile_refine_usecase,
    get_complete_profile_translate_usecase,
    get_fail_ingestion_usecase,
    get_ingest_profile_usecase,
    get_list_profiles_usecase,
    get_repo,
    get_submit_raw_text_usecase,
    verify_token,
)
from api.limiter_config import limiter

logger = get_logger("api-profiles")


# Create the uploads directory if it does not exist
UPLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "uploads")
)
os.makedirs(UPLOADS_DIR, exist_ok=True)

router = APIRouter(dependencies=[Depends(verify_token)])


class IngestionComplete(BaseModel):
    profile: dict


class IngestionFail(BaseModel):
    error_message: str


class SubmitRawTextRequest(BaseModel):
    raw_text: str
    name: str | None = None
    email: str | None = None


class ProfileDetectionResult(BaseModel):
    profile_id: int
    language_code: str


class ProfileTranslationResult(BaseModel):
    profile_id: int
    raw_text_en: str


class ProfileRefinementResult(BaseModel):
    profile_id: int
    profile: dict


class ProfileFieldsUpdate(BaseModel):
    name: str | None = None
    highest_degree: str | None = None
    skills: list[str] | str | None = None
    research_interests: list[str] | str | None = None
    preferred_locations: list[str] | str | None = None
    languages: list[dict[str, str]] | str | None = None


@router.post("/profiles/upload-cv", status_code=202)
@limiter.limit("5/minute")
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    email: str | None = Form(None),
    name: str | None = Form(None),
    telegram_chat_id: str | None = Form(None),
    usecase: IngestCandidateProfileUseCase = Depends(get_ingest_profile_usecase),
):
    filename = file.filename or "cv.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF files are supported.",
        )

    # Read uploaded file content bytes directly
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file.")

    # 2. Register placeholder profile and trigger ingestion task asynchronously
    try:
        saved_profile = usecase.execute(
            file_name=filename,
            file_content=content,
            email=email,
            name=name,
            telegram_chat_id=telegram_chat_id,
        )
        logger.info(f"Successfully registered CV ingestion for profile ID: {saved_profile.id}")
        return saved_profile.to_dict()
    except Exception as e:
        logger.error("Error registering CV ingestion", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register CV ingestion task: {e!s}")


@router.post("/profiles/claim-ingest")
@limiter.limit("60/minute")
async def claim_ingest_task(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimIngestionUseCase = Depends(get_claim_ingestion_usecase),
):
    profile = usecase.execute(body.agent_name)
    if profile is None:
        return {"profile": None, "message": "No pending ingestion tasks available"}
    return {"profile": profile.to_dict()}


@router.put("/profiles/complete-ingest/{profile_id}")
@limiter.limit("60/minute")
async def complete_ingest_task(
    request: Request,
    profile_id: int,
    body: IngestionComplete,
    usecase: CompleteIngestionUseCase = Depends(get_complete_ingestion_usecase),
):
    from core.domain.models.profile import CandidateProfile

    profile_domain = CandidateProfile.from_dict(body.profile)
    usecase.execute(profile_id, profile_domain)
    return {"status": "completed", "profile_id": profile_id}


@router.put("/profiles/fail-ingest/{profile_id}")
@limiter.limit("60/minute")
async def fail_ingest_task(
    request: Request,
    profile_id: int,
    body: IngestionFail,
    usecase: FailIngestionUseCase = Depends(get_fail_ingestion_usecase),
):
    usecase.execute(profile_id, body.error_message)
    return {"status": "failed", "profile_id": profile_id}


class MarkProfilesNotifiedRequest(BaseModel):
    profile_ids: list[int]


@router.get("/profiles/unnotified-completed")
@limiter.limit("60/minute")
async def get_unnotified_completed_profiles(
    request: Request,
    limit: int = 10,
    repo=Depends(get_repo),
):
    profiles = repo.profiles.get_unnotified_completed(limit=limit)
    return [p.to_dict() for p in profiles]


@router.put("/profiles/mark-notified")
@limiter.limit("60/minute")
async def mark_profiles_notified(
    request: Request,
    body: MarkProfilesNotifiedRequest,
    repo=Depends(get_repo),
):
    count = repo.profiles.mark_notified(body.profile_ids)
    return {"status": "success", "marked_count": count}


@router.get("/profiles/{profile_id}")
@limiter.limit("30/minute")
async def get_profile(
    request: Request,
    profile_id: int,
    usecase: GetCandidateProfileUseCase = Depends(get_candidate_profile_usecase),
):
    profile = usecase.execute(profile_id)
    if not profile:
        raise HTTPException(
            status_code=404, detail=f"Candidate profile with ID {profile_id} not found."
        )
    return profile.to_dict()


@router.get("/profiles")
@limiter.limit("60/minute")
async def get_all_profiles(
    request: Request,
    usecase=Depends(get_list_profiles_usecase),
):
    profiles = usecase.execute()
    return [p.to_dict() for p in profiles]


@router.put("/profiles/submit-raw-text/{profile_id}")
@limiter.limit("60/minute")
async def submit_raw_text(
    request: Request,
    profile_id: int,
    body: SubmitRawTextRequest,
    usecase: SubmitRawTextUseCase = Depends(get_submit_raw_text_usecase),
):
    usecase.execute(profile_id, body.raw_text, body.name, body.email)
    return {"status": "success", "profile_id": profile_id}


@router.post("/profiles/claim-detect")
@limiter.limit("60/minute")
async def claim_profile_detect(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimProfileDetectionUseCase = Depends(get_claim_profile_detect_usecase),
):
    profile = usecase.execute(body.agent_name)
    if profile is None:
        return {
            "profile": None,
            "message": "No pending profile detection tasks available",
        }
    return {"profile": profile.to_dict()}


@router.put("/profiles/detect")
@limiter.limit("60/minute")
async def complete_profile_detect(
    request: Request,
    body: ProfileDetectionResult,
    usecase: CompleteProfileDetectionUseCase = Depends(get_complete_profile_detect_usecase),
):
    usecase.execute(body.profile_id, body.language_code)
    return {"status": "success", "profile_id": body.profile_id}


@router.post("/profiles/claim-translate")
@limiter.limit("1200/minute")
async def claim_profile_translate(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimProfileTranslationUseCase = Depends(get_claim_profile_translate_usecase),
):
    profile = usecase.execute(body.agent_name)
    if profile is None:
        return {
            "profile": None,
            "message": "No pending profile translation tasks available",
        }
    return {"profile": profile.to_dict()}


@router.put("/profiles/translate")
@limiter.limit("60/minute")
async def complete_profile_translate(
    request: Request,
    body: ProfileTranslationResult,
    usecase: CompleteProfileTranslationUseCase = Depends(get_complete_profile_translate_usecase),
):
    usecase.execute(body.profile_id, body.raw_text_en)
    return {"status": "success", "profile_id": body.profile_id}


@router.post("/profiles/claim-refine")
@limiter.limit("60/minute")
async def claim_profile_refine(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimProfileRefinementUseCase = Depends(get_claim_profile_refine_usecase),
):
    profile = usecase.execute(body.agent_name)
    if profile is None:
        return {
            "profile": None,
            "message": "No pending profile refinement tasks available",
        }
    return {"profile": profile.to_dict()}


@router.put("/profiles/refine")
@limiter.limit("60/minute")
async def complete_profile_refine(
    request: Request,
    body: ProfileRefinementResult,
    usecase: CompleteProfileRefinementUseCase = Depends(get_complete_profile_refine_usecase),
):
    from core.domain.models.profile import CandidateProfile

    profile_domain = CandidateProfile.from_dict(body.profile)
    final_id = usecase.execute(body.profile_id, profile_domain)
    return {"status": "success", "profile_id": final_id}


@router.get("/profiles/by-chat-id/{chat_id}")
@limiter.limit("60/minute")
async def get_profiles_by_chat_id(
    request: Request,
    chat_id: str,
    repo=Depends(get_repo),
):
    profiles = repo.profiles.get_by_telegram_chat_id(chat_id)
    return [p.to_dict() for p in profiles]


@router.patch("/profiles/{profile_id}")
@limiter.limit("30/minute")
async def update_profile_fields(
    request: Request,
    profile_id: int,
    body: ProfileFieldsUpdate,
    repo=Depends(get_repo),
):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    updated = repo.profiles.update_profile_fields(profile_id, fields)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Candidate profile with ID {profile_id} not found."
        )
    return updated.to_dict()


@router.delete("/profiles/by-telegram-chat-id/{chat_id}")
@limiter.limit("10/minute")
async def delete_profiles_by_chat_id(
    request: Request,
    chat_id: str,
    repo=Depends(get_repo),
):
    deleted = repo.profiles.delete_by_telegram_chat_id(chat_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No candidate profile found for Telegram chat ID {chat_id}.",
        )
    return {"status": "success", "message": f"All profile data for chat {chat_id} deleted."}


@router.delete("/profiles/{profile_id}")
@limiter.limit("10/minute")
async def delete_profile_by_id(
    request: Request,
    profile_id: int,
    repo=Depends(get_repo),
):
    deleted = repo.profiles.delete_by_id(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate profile with ID {profile_id} not found.",
        )
    return {"status": "success", "message": f"Profile #{profile_id} deleted successfully."}



