from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Job:
    title: str
    url: str
    source: str

    deadline: Optional[str] = None
    employer: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None

    required_skills: Optional[list[str]] = None
    education_level: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    language_code: Optional[str] = None
    description_en: Optional[str] = None
    requirements_en: Optional[str] = None

    skill_embedding: Optional[list[float]] = None
    research_embedding: Optional[list[float]] = None

    def is_detail_scraped(self) -> bool:
        return self.description is not None

    def is_refined(self) -> bool:
        return self.required_skills is not None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Job:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
