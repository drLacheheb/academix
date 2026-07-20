from core.usecases.detection import (
    ClaimDetectionJobUseCase,
    CompleteDetectionUseCase,
    FailDetectionUseCase,
)
from core.usecases.translation import (
    ClaimTranslationJobUseCase,
    CompleteTranslationUseCase,
    FailTranslationUseCase,
)
from core.usecases.refinement import (
    ClaimRefinementJobUseCase,
    CompleteRefinementUseCase,
    FailRefinementUseCase,
)
from core.usecases.status import GetDatabaseStatusUseCase
from core.usecases.details import UpdateJobDetailsUseCase
from core.usecases.check_known_urls import CheckKnownUrlsUseCase
from core.usecases.create_jobs import CreateJobsUseCase
from core.usecases.pending_details import GetPendingDetailsUseCase

from core.usecases.profiles import (
    IngestCandidateProfileUseCase,
    GetCandidateProfileUseCase,
    ClaimIngestionUseCase,
    CompleteIngestionUseCase,
    FailIngestionUseCase,
    SubmitRawTextUseCase,
    ClaimProfileDetectionUseCase,
    CompleteProfileDetectionUseCase,
    ClaimProfileTranslationUseCase,
    CompleteProfileTranslationUseCase,
    ClaimProfileRefinementUseCase,
    CompleteProfileRefinementUseCase,
)
from core.usecases.matching import (
    ClaimMatchingTaskUseCase,
    SubmitTaskMatchesUseCase,
    FailMatchingTaskUseCase,
    GetCandidateMatchesUseCase,
    ClaimMatchExplanationUseCase,
    CompleteMatchExplanationUseCase,
    FailMatchExplanationUseCase,
)

__all__ = [
    "ClaimDetectionJobUseCase",
    "CompleteDetectionUseCase",
    "FailDetectionUseCase",
    "ClaimTranslationJobUseCase",
    "CompleteTranslationUseCase",
    "FailTranslationUseCase",
    "ClaimRefinementJobUseCase",
    "CompleteRefinementUseCase",
    "FailRefinementUseCase",
    "GetDatabaseStatusUseCase",
    "UpdateJobDetailsUseCase",
    "CheckKnownUrlsUseCase",
    "CreateJobsUseCase",
    "GetPendingDetailsUseCase",
    "IngestCandidateProfileUseCase",
    "GetCandidateProfileUseCase",
    "ClaimIngestionUseCase",
    "CompleteIngestionUseCase",
    "FailIngestionUseCase",
    "SubmitRawTextUseCase",
    "ClaimProfileDetectionUseCase",
    "CompleteProfileDetectionUseCase",
    "ClaimProfileTranslationUseCase",
    "CompleteProfileTranslationUseCase",
    "ClaimProfileRefinementUseCase",
    "CompleteProfileRefinementUseCase",
    "ClaimMatchingTaskUseCase",
    "SubmitTaskMatchesUseCase",
    "FailMatchingTaskUseCase",
    "GetCandidateMatchesUseCase",
    "ClaimMatchExplanationUseCase",
    "CompleteMatchExplanationUseCase",
    "FailMatchExplanationUseCase",
]
