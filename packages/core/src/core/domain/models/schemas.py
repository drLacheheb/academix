from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

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
    job_details: str


class JobRefinementExtraction(BaseModel):
    employer: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the full official name of the hiring university, research institute, "
            "or organization (e.g., Delft University of Technology, Max Planck Institute)."
        ),
    )
    deadline: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the application closing date in standard ISO YYYY-MM-DD format. "
            "Rule: If no deadline or date is explicitly stated, return None."
        ),
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Rule: Exhaustively extract ALL concrete hard skills, methodological techniques, "
            "analytical tools, software, and operational frameworks. "
            "This must encompass both technical STEM skills and specialized methodological "
            "approaches utilized in the humanities and social sciences. "
            "Negative Rule: Do not extract subjective interpersonal abilities, generic "
            "behavioral traits, or broad academic disciplines."
        ),
    )
    research_interests: list[str] = Field(
        alias="granular_research_domains",
        default_factory=list,
        description=(
            "Rule: Extract specific, highly granular research domains and academic niches "
            "(e.g., Network Anomaly Detection, Embedded Telemetry). "
            "Rule: If a domain contains an ampersand (&), you must split it into two "
            "separate domains. "
            "Rule: Expand all acronyms (e.g. IoT becomes Internet of Things). "
            "Rule: Do not extract software tools or languages (e.g. PyTorch, React, Python)."
        ),
    )
    education_level: EducationLevel = Field(
        description=(
            "Rule: Extract the minimum academic degree required. Must be one of: "
            "Bachelor, Master, PhD."
        ),
    )
    degree_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Rule: Extract the major or discipline required by the degree (e.g., Computer "
            "Science, Molecular Biology). "
            "Rule: If multiple fields are allowed, extract each as a separate item in the list."
        ),
    )
    city: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the normalized city name in Title Case. "
            "Negative Rule: Do not include country or state."
        ),
    )
    country: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the full English country name in Title Case. "
            "Negative Rule: Do not use abbreviations."
        ),
    )

    @field_validator("required_skills", "research_interests", mode="before")
    @classmethod
    def default_none_to_list(cls, v: list[str] | None) -> list[str]:
        return v if v is not None else []

    @field_validator("education_level", mode="before")
    @classmethod
    def normalize_education(cls, v: str | None) -> EducationLevel:
        if not v or not isinstance(v, str):
            raise ValueError("education_level must be provided as a string")
        v_lower = v.strip().lower()
        if any(
            b in v_lower for b in ["bachelor", "bsc", "hbo", "licence", "license", "b.s.", "bs"]
        ):
            return EducationLevel.BACHELOR
        if any(m in v_lower for m in ["master", "msc", "magister", "m.s.", "ms"]):
            return EducationLevel.MASTER
        if any(p in v_lower for p in ["phd", "doctor", "postdoc", "dr"]):
            return EducationLevel.PHD
        raise ValueError(
            f"Could not normalize degree from '{v}'. Must be Bachelor, Master, or PhD."
        )


class LanguageProficiency(BaseModel):
    language: str = Field(
        description=(
            "Rule: Extract the name of the spoken language in English. "
            "Negative Rule: Do not extract programming languages here."
        )
    )
    proficiency: LanguageProficiencyLevel | None = Field(
        default=LanguageProficiencyLevel.FLUENT,
        description=(
            "Rule: Categorize the proficiency level. "
            "Negative Rule: Do not invent new proficiency levels."
        ),
    )


class CandidateCvExtraction(BaseModel):
    name: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the full name of the candidate. "
            "Negative Rule: Do not include titles like Dr. or Prof."
        ),
    )
    email: str | None = Field(
        default=None,
        description=(
            "Rule: Extract the primary email address. Negative Rule: Do not include mailto: links."
        ),
    )
    highest_degree: EducationLevel = Field(
        description=(
            "Rule: Extract the highest earned academic degree. Must be one of: "
            "Bachelor, Master, PhD. "
            "Rule: Do not skip this field. Look carefully through the entire CV."
        ),
    )
    degree_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Rule: Extract the major or discipline of the earned degree (e.g., Computer "
            "Science, Molecular Biology). "
            "Rule: If the candidate has multiple degrees, extract all fields."
        ),
    )
    skills: list[str] = Field(
        default_factory=list,
        description=(
            "Rule: Exhaustively extract ALL concrete hard skills, methodological techniques, "
            "analytical tools, software, and operational frameworks. "
            "This must encompass both technical STEM skills and specialized methodological "
            "approaches utilized in the humanities and social sciences. "
            "Negative Rule: Do not extract subjective interpersonal abilities, generic "
            "behavioral traits, or broad academic disciplines."
        ),
    )
    languages: list[LanguageProficiency] = Field(
        default_factory=list,
        description=(
            "Rule: Extract all spoken languages. "
            "Negative Rule: Do not extract programming languages here."
        ),
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description=(
            "Rule: Extract preferred cities or countries explicitly stated. "
            "Negative Rule: Do not extract previous work locations unless explicitly "
            "stated as preferred targets."
        ),
    )
    research_interests: list[str] = Field(
        alias="granular_research_domains",
        default_factory=list,
        description=(
            "Rule: Extract specific, highly granular research domains and academic niches "
            "(e.g., Network Anomaly Detection, Embedded Telemetry). "
            "Rule: If a domain contains an ampersand (&), you must split it into two "
            "separate domains. "
            "Rule: Expand all acronyms (e.g. IoT becomes Internet of Things). "
            "Rule: Do not extract software tools or languages (e.g. PyTorch, React, Python)."
        ),
    )

    @field_validator("highest_degree", mode="before")
    @classmethod
    def normalize_highest_degree(cls, v: str | None) -> EducationLevel:
        if not v or not isinstance(v, str):
            raise ValueError("highest_degree must be provided as a string")
        v_lower = v.strip().lower()
        if any(
            b in v_lower for b in ["bachelor", "bsc", "hbo", "licence", "license", "b.s.", "bs"]
        ):
            return EducationLevel.BACHELOR
        if any(m in v_lower for m in ["master", "msc", "magister", "m.s.", "ms"]):
            return EducationLevel.MASTER
        if any(p in v_lower for p in ["phd", "doctor", "postdoc", "dr"]):
            return EducationLevel.PHD
        raise ValueError(
            f"Could not normalize degree from '{v}'. Must be Bachelor, Master, or PhD."
        )

    @field_validator(
        "skills",
        "languages",
        "preferred_locations",
        "research_interests",
        mode="before",
    )
    @classmethod
    def default_none_to_list(cls, v: list | None) -> list:
        return v if v is not None else []


class MatchReason(BaseModel):
    category: MatchCategory = Field(
        description=(
            "Rule: Categorize the match strictly into one of the allowed categories. "
            "Negative Rule: Do not invent new categories."
        )
    )
    description: str = Field(
        description=(
            "Rule: Provide a concise description of the matching point in exactly one sentence. "
            "Negative Rule: Do not use vague language."
        )
    )


class MatchExplanationExtraction(BaseModel):
    reasons: list[MatchReason] = Field(
        min_length=1,
        description=(
            "Rule: Provide a structured breakdown of key matching reasons. "
            "Negative Rule: Do not provide an empty list."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def unwrap_outer_class(cls, values: Any) -> Any:
        if isinstance(values, dict) and "MatchExplanationExtraction" in values:
            return values["MatchExplanationExtraction"]
        return values


class RefinementResult(BaseModel):
    url: str
    employer: str | None = None
    deadline: str | None = None
    required_skills: list[str]
    research_interests: list[str] = Field(default_factory=list)
    education_level: str | None = None
    degree_fields: list[str] = Field(default_factory=list)
    city: str | None = None
    country: str | None = None
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None


class EmbeddingJobResult(BaseModel):
    url: str
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None
    degree_embedding: list[float] | None = None


class ProfileEmbeddingResult(BaseModel):
    profile_id: int
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None
    degree_embedding: list[float] | None = None


class ClaimRequest(BaseModel):
    agent_name: str


class KnownUrlsRequest(BaseModel):
    urls: list[str]


class TranslationResult(BaseModel):
    url: str
    job_details_en: str | None = None


class MatchResult(BaseModel):
    candidate_id: int
    job_url: str
    score: float
    degree_eligible: bool
    skill_score: float
    research_score: float


class MatchingTaskComplete(BaseModel):
    task_id: int
    matches: list[MatchResult]


class MatchExplanationComplete(BaseModel):
    match_id: int
    explanation: str
