from pydantic import BaseModel


class JobStubCreate(BaseModel):
    title: str
    url: str
    source: str


class JobDetailUpdate(BaseModel):
    url: str
    description: str | None = None
    requirements: str | None = None
    deadline: str | None = None
    employer: str | None = None
    location: str | None = None


class RefinementResult(BaseModel):
    url: str
    required_skills: list[str]
    education_level: str | None = None
    city: str | None = None
    country: str | None = None
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None


class ClaimRequest(BaseModel):
    agent_name: str


class KnownUrlsRequest(BaseModel):
    urls: list[str]


class DetectionResult(BaseModel):
    url: str
    language_code: str


class TranslationResult(BaseModel):
    url: str
    description_en: str | None = None
    requirements_en: str | None = None


class MatchResult(BaseModel):
    candidate_id: int
    job_url: str
    score: float
    degree_eligible: bool
    language_eligible: bool
    skill_score: float
    research_score: float


class MatchingTaskComplete(BaseModel):
    task_id: int
    matches: list[MatchResult]


class MatchExplanationComplete(BaseModel):
    match_id: int
    explanation: str


class CheckpointUpdate(BaseModel):
    source: str
    url: str
