from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Job:
    title: str
    url: str
    source: str

    deadline: str | None = None
    employer: str | None = None
    job_details: str | None = None

    required_skills: list[str] | None = None
    research_interests: list[str] | None = None
    education_level: str | None = None
    degree_fields: list[str] | None = None
    city: str | None = None
    country: str | None = None

    job_details_en: str | None = None

    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None
    degree_embedding: list[float] | None = None

    def is_detail_scraped(self) -> bool:
        return self.job_details is not None

    def is_refined(self) -> bool:
        return self.required_skills is not None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Job:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
