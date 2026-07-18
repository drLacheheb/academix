import os
import shutil
import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request

from api.dependencies import (
    get_ingest_profile_usecase,
    get_candidate_profile_usecase,
    get_list_profiles_usecase,
    verify_token,
)
from api.limiter_config import limiter
from core.usecases import IngestCandidateProfileUseCase, GetCandidateProfileUseCase

logger = logging.getLogger(__name__)

# Create the uploads directory if it does not exist
UPLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "uploads")
)
os.makedirs(UPLOADS_DIR, exist_ok=True)

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/profiles/upload-cv")
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

    # 1. Save uploaded file to the uploads directory
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{file.filename}"
    saved_file_path = os.path.join(UPLOADS_DIR, safe_filename)

    try:
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved uploaded CV to {saved_file_path}")
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # 2. Process CV and extract structured profile using Gemma-4 GGUF Use Case
    try:
        saved_profile = usecase.execute(
            file_path=saved_file_path, email=email, name=name
        )
        logger.info(
            f"Successfully processed and saved profile for email: {saved_profile.email}"
        )

        return saved_profile.to_dict()

    except ValueError as ve:
        # Cleanup uploaded file if validation failed
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing CV file: {e}")
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(
            status_code=500, detail=f"Failed to parse and extract CV metadata: {str(e)}"
        )


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
