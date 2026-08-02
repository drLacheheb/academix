from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class CandidateProfile:
    id: int | None = None
    name: str | None = None
    email: str | None = None
    cv_file_path: str | None = None
    raw_text: str | None = None
    language_code: str | None = None
    raw_text_en: str | None = None
    highest_degree: str | None = None
    skills: list[str] | None = None
    languages: list[dict[str, str]] | None = None
    experience: list[dict[str, Any]] | None = None
    preferred_locations: list[str] | None = None
    research_interests: list[str] | None = None
    skill_embedding: list[float] | None = None
    research_embedding: list[float] | None = None
    status: str = "INGESTING"
    status_message: str | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    telegram_chat_id: str | None = None
    is_notified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CandidateProfile:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
