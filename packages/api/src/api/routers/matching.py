import logging
from fastapi import APIRouter, Depends, Request
from core.domain.models.schemas import (
    ClaimRequest,
    MatchingTaskComplete,
    MatchExplanationComplete,
)
from core.domain.models.match import Match
from api.dependencies import (
    get_claim_matching_task_usecase,
    ClaimMatchingTaskUseCase,
    get_submit_task_matches_usecase,
    SubmitTaskMatchesUseCase,
    get_fail_matching_task_usecase,
    FailMatchingTaskUseCase,
    get_candidate_matches_usecase,
    GetCandidateMatchesUseCase,
    get_claim_match_explanation_usecase,
    ClaimMatchExplanationUseCase,
    get_complete_match_explanation_usecase,
    CompleteMatchExplanationUseCase,
    get_fail_match_explanation_usecase,
    FailMatchExplanationUseCase,
    verify_token,
)
from api.limiter_config import limiter

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("/matches/claim")
@limiter.limit("60/minute")
async def claim_matching_task(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimMatchingTaskUseCase = Depends(get_claim_matching_task_usecase),
):
    task = usecase.execute(body.agent_name)
    if task is None:
        return {"task": None, "message": "No pending matching tasks available"}
    return {"task": task.to_dict()}


@router.put("/matches/complete")
@limiter.limit("60/minute")
async def submit_task_matches(
    request: Request,
    body: MatchingTaskComplete,
    usecase: SubmitTaskMatchesUseCase = Depends(get_submit_task_matches_usecase),
):
    # Convert MatchResult list from Pydantic into Match domain model list
    domain_matches = [
        Match(
            candidate_id=m.candidate_id,
            job_url=m.job_url,
            score=m.score,
            degree_eligible=m.degree_eligible,
            language_eligible=m.language_eligible,
            skill_score=m.skill_score,
            research_score=m.research_score,
        )
        for m in body.matches
    ]
    usecase.execute(body.task_id, domain_matches)
    return {"status": "completed", "task_id": body.task_id}


@router.put("/matches/fail/{task_id}")
@limiter.limit("60/minute")
async def fail_matching_task(
    request: Request,
    task_id: int,
    usecase: FailMatchingTaskUseCase = Depends(get_fail_matching_task_usecase),
):
    usecase.execute(task_id)
    return {"status": "failed", "task_id": task_id}


@router.post("/matches/claim-explain")
@limiter.limit("60/minute")
async def claim_match_explanation(
    request: Request,
    body: ClaimRequest,
    usecase: ClaimMatchExplanationUseCase = Depends(
        get_claim_match_explanation_usecase
    ),
):
    match = usecase.execute(body.agent_name)
    if match is None:
        return {"match": None, "message": "No pending explanations available"}
    return {"match": match.to_dict()}


@router.put("/matches/complete-explain")
@limiter.limit("60/minute")
async def complete_match_explanation(
    request: Request,
    body: MatchExplanationComplete,
    usecase: CompleteMatchExplanationUseCase = Depends(
        get_complete_match_explanation_usecase
    ),
):
    usecase.execute(body.match_id, body.explanation)
    return {"status": "completed", "match_id": body.match_id}


@router.put("/matches/fail-explain/{match_id}")
@limiter.limit("60/minute")
async def fail_match_explanation(
    request: Request,
    match_id: int,
    usecase: FailMatchExplanationUseCase = Depends(get_fail_match_explanation_usecase),
):
    usecase.execute(match_id)
    return {"status": "failed", "match_id": match_id}


@router.get("/profiles/{profile_id}/matches")
@limiter.limit("60/minute")
async def get_candidate_matches(
    request: Request,
    profile_id: int,
    limit: int = 20,
    usecase: GetCandidateMatchesUseCase = Depends(get_candidate_matches_usecase),
):
    matches = usecase.execute(profile_id, limit)
    return {"matches": [m.to_dict() for m in matches]}
