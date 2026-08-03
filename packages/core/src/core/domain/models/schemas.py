from pydantic import BaseModel, Field, field_validator

from core.domain.constants import (
    EducationLevel,
    LanguageProficiencyLevel,
    MatchCategory,
)


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

    @field_validator("required_skills", mode="before")
    @classmethod
    def default_none_to_list(cls, v: list[str] | None) -> list[str]:
        return v if v is not None else []

    @field_validator("education_level", mode="before")
    @classmethod
    def normalize_education(cls, v: str | None) -> EducationLevel | None:
        if not v or not isinstance(v, str):
            return None
        v_lower = v.strip().lower()
        if any(b in v_lower for b in ["bachelor", "bsc", "hbo", "licence", "license"]):
            return EducationLevel.BACHELOR
        if any(m in v_lower for m in ["master", "msc", "magister"]):
            return EducationLevel.MASTER
        if any(p in v_lower for p in ["phd", "doctor", "postdoc", "dr"]):
            return EducationLevel.PHD
        return None


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

    @field_validator("highest_degree", mode="before")
    @classmethod
    def normalize_highest_degree(cls, v: str | None) -> EducationLevel | None:
        if not v or not isinstance(v, str):
            return None
        v_lower = v.strip().lower()
        if any(b in v_lower for b in ["bachelor", "bsc", "hbo", "licence", "license"]):
            return EducationLevel.BACHELOR
        if any(m in v_lower for m in ["master", "msc", "magister"]):
            return EducationLevel.MASTER
        if any(p in v_lower for p in ["phd", "doctor", "postdoc", "dr"]):
            return EducationLevel.PHD
        return None

    @field_validator(
        "skills",
        "languages",
        "experience",
        "preferred_locations",
        "research_interests",
        mode="before",
    )
    @classmethod
    def default_none_to_list(cls, v: list | None) -> list:
        return v if v is not None else []


class MatchReason(BaseModel):
    category: MatchCategory = Field(description="Category of match")
    description: str = Field(description="Detailed description of the specific matching point.")


class MatchExplanationExtraction(BaseModel):
    reasons: list[MatchReason] = Field(
        min_length=1,
        description="Structured breakdown of key matching reasons. MUST contain at least 1 reason.",
    )


class RefinementResult(BaseModel):
    url: str
    required_skills: list[str]
    education_level: str | None = None
    city: str | None = None
    country: str | None = None
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None


class EmbeddingJobResult(BaseModel):
    url: str
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None


class ProfileEmbeddingResult(BaseModel):
    profile_id: int
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
