from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Match:
    candidate_id: int
    job_url: str
    score: float
    degree_eligible: bool
    language_eligible: bool
    skill_score: float
    research_score: float
    id: int | None = None
    explanation: str | None = None
    explanation_status: str = "pending"
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Match:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
