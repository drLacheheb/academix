import os
from enum import StrEnum

STALE_CLAIM_TIMEOUT_MINUTES = int(os.getenv("STALE_CLAIM_TIMEOUT_MINUTES", "10"))


class JobStatus(StrEnum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EducationLevel(StrEnum):
    BACHELOR = "Bachelor"
    MASTER = "Master"
    PHD = "PhD"


class LanguageProficiencyLevel(StrEnum):
    NATIVE = "Native"
    FLUENT = "Fluent"
    INTERMEDIATE = "Intermediate"
    BASIC = "Basic"
