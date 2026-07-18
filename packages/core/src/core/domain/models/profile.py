from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Any
from datetime import datetime


@dataclass
class CandidateProfile:
    name: str
    email: str
    id: Optional[int] = None
    cv_file_path: Optional[str] = None
    raw_text: Optional[str] = None
    highest_degree: Optional[str] = None
    skills: Optional[list[str]] = None
    languages: Optional[list[dict[str, str]]] = None
    experience: Optional[list[dict[str, Any]]] = None
    preferred_locations: Optional[list[str]] = None
    research_interests: Optional[list[str]] = None
    skill_embedding: Optional[list[float]] = None
    research_embedding: Optional[list[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CandidateProfile:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
