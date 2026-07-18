from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime


@dataclass
class MatchingTask:
    entity_type: str        # "candidate" or "job"
    entity_id: str          # profile_id (str) or job_url
    id: Optional[int] = None
    status: str = "pending" # pending | claimed | completed | failed
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MatchingTask:
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
