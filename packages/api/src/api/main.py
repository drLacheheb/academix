from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import update as sa_update

from core.models import (
    Job,
    JobStubCreate,
    JobDetailUpdate,
    RefinementResult,
    ClaimRequest,
    KnownUrlsRequest,
    DetectionResult,
    TranslationResult,
)
from core.db.repository import DatabaseJobRepository, JobModel
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


_repo: DatabaseJobRepository | None = None


def get_repo() -> DatabaseJobRepository:
    global _repo
    if _repo is None:
        _repo = DatabaseJobRepository(get_database_url())
    return _repo


async def verify_token(authorization: str = Header(...)):
    expected = f"Bearer {get_api_secret()}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/status")
@limiter.limit("120/minute")
async def health_status(request: Request, repo: DatabaseJobRepository = Depends(get_repo)):
    return repo.get_status()


@app.post("/jobs/known-urls", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def check_known_urls(
    request: Request,
    body: KnownUrlsRequest,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    known = repo.get_known_urls(body.urls)
    return {"known_urls": list(known)}


@app.post("/jobs", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def create_jobs(
    request: Request,
    stubs: list[JobStubCreate],
    repo: DatabaseJobRepository = Depends(get_repo),
):
    jobs = [
        Job(title=s.title, url=s.url, source=s.source)
        for s in stubs
    ]
    repo.save(jobs)
    return {"inserted": len(jobs)}


@app.get("/jobs/pending-details", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def get_pending_details(
    request: Request,
    source: Optional[str] = None,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    jobs = repo.get_unstored(source=source)
    return [j.to_dict() for j in jobs]


@app.put("/jobs/details", dependencies=[Depends(verify_token)])
@limiter.limit("30/minute")
async def update_job_details(
    request: Request,
    details: list[JobDetailUpdate],
    repo: DatabaseJobRepository = Depends(get_repo),
):
    for d in details:
        session = repo._SessionLocal()
        try:
            values = {}
            if d.description is not None:
                values["description"] = d.description
            if d.requirements is not None:
                values["requirements"] = d.requirements
            if d.deadline is not None:
                values["deadline"] = d.deadline
            if d.employer is not None:
                values["employer"] = d.employer
            if d.location is not None:
                values["location"] = d.location
            if values:
                session.execute(
                    sa_update(JobModel).where(JobModel.url == d.url).values(**values)
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    return {"updated": len(details)}


@app.post("/jobs/claim-detect", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def claim_detection_job(
    request: Request,
    body: ClaimRequest,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    job = repo.claim_next_for_detection(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/detect", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_detection(
    request: Request,
    result: DetectionResult,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    repo.complete_detection(
        url=result.url,
        language_code=result.language_code,
    )
    return {"status": "completed", "url": result.url}


@app.post("/jobs/claim-translate", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def claim_translation_job(
    request: Request,
    body: ClaimRequest,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    job = repo.claim_next_for_translation(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/translate", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_translation(
    request: Request,
    result: TranslationResult,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    repo.complete_translation(
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
    repo: DatabaseJobRepository = Depends(get_repo),
):
    job = repo.claim_next_for_refinement(body.agent_name)
    if job is None:
        return {"job": None, "message": "No pending jobs available"}
    return {"job": job.to_dict()}


@app.put("/jobs/refine", dependencies=[Depends(verify_token)])
@limiter.limit("60/minute")
async def submit_refinement(
    request: Request,
    result: RefinementResult,
    repo: DatabaseJobRepository = Depends(get_repo),
):
    repo.complete_refinement(
        url=result.url,
        required_skills=result.required_skills,
        education_level=result.education_level,
        city=result.city,
        country=result.country,
    )
    return {"status": "completed", "url": result.url}



