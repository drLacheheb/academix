from pydantic import BaseModel, Field

from core.domain.constants import EducationLevel, LanguageProficiencyLevel


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


class JobRefinementExtraction(BaseModel):
    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Specific tools, techniques, programming languages, lab methods, "
            "or specialized academic research domains."
        ),
    )
    education_level: EducationLevel | None = Field(
        default=None,
        description="Minimum academic degree required to apply.",
    )
    city: str | None = Field(
        default=None,
        description="Normalized city name in Title Case.",
    )
    country: str | None = Field(
        default=None,
        description="Full English country name in Title Case.",
    )


class LanguageProficiency(BaseModel):
    language: str = Field(description="Name of spoken language in English.")
    proficiency: LanguageProficiencyLevel | None = Field(
        default=LanguageProficiencyLevel.FLUENT,
        description="Proficiency level.",
    )


class ExperienceItem(BaseModel):
    role: str = Field(description="Position or job title.")
    organization: str | None = Field(
        default=None, description="University, laboratory, or company name."
    )
    from_date: str | None = Field(default=None, description="Start year or date.")
    to_date: str | None = Field(default=None, description="End year/date or Present.")
    description: str | None = Field(
        default=None, description="Concise summary of responsibilities and achievements."
    )


class CandidateCvExtraction(BaseModel):
    name: str | None = Field(default=None, description="Full name of candidate.")
    email: str | None = Field(default=None, description="Primary email address of candidate.")
    highest_degree: EducationLevel | None = Field(
        default=None,
        description="Highest earned academic degree.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of concrete technical, scientific, lab, or research skills.",
    )
    languages: list[LanguageProficiency] = Field(
        default_factory=list,
        description="List of spoken languages with proficiency levels.",
    )
    experience: list[ExperienceItem] = Field(
        default_factory=list,
        description="List of past academic or professional positions held.",
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description="Target preferred cities or countries explicitly stated in candidate CV.",
    )
    research_interests: list[str] = Field(
        default_factory=list,
        description="Core scientific research topics or specialized subfields.",
    )


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
