import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from pydantic import BaseModel

from api.dependencies import (
    get_ingest_profile_usecase,
    get_candidate_profile_usecase,
    get_list_profiles_usecase,
    get_claim_ingestion_usecase,
    get_complete_ingestion_usecase,
    get_fail_ingestion_usecase,
    verify_token,
)
from api.limiter_config import limiter
from core.usecases import (
    IngestCandidateProfileUseCase,
    GetCandidateProfileUseCase,
    ClaimIngestionUseCase,
    CompleteIngestionUseCase,
    FailIngestionUseCase,
)
from core.domain.models.schemas import ClaimRequest

logger = logging.getLogger(__name__)

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


@router.post("/profiles/upload-cv", status_code=202)
@limiter.limit("5/minute")
async def upload_cv(
    request: Request,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    usecase: IngestCandidateProfileUseCase = Depends(get_ingest_profile_usecase),
):
    if not file.filename.lower().endswith(".pdf"):
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
            file_name=file.filename,
            file_content=content,
            email=email,
            name=name,
        )
        logger.info(
            f"Successfully registered CV ingestion for profile ID: {saved_profile.id}"
        )
        return saved_profile.to_dict()
    except Exception as e:
        logger.error(f"Error registering CV ingestion: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to register CV ingestion task: {str(e)}"
        )


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
