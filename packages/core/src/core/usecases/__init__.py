from core.usecases.check_known_urls import CheckKnownUrlsUseCase
from core.usecases.create_jobs import CreateJobsUseCase
from core.usecases.details import UpdateJobDetailsUseCase
from core.usecases.detection import (
    ClaimDetectionJobUseCase,
    CompleteDetectionUseCase,
    FailDetectionUseCase,
)
from core.usecases.matching import (
    ClaimMatchExplanationUseCase,
    ClaimMatchingTaskUseCase,
    CompleteMatchExplanationUseCase,
    FailMatchExplanationUseCase,
    FailMatchingTaskUseCase,
    GetCandidateMatchesUseCase,
    SubmitTaskMatchesUseCase,
)
from core.usecases.pending_details import GetPendingDetailsUseCase
from core.usecases.profiles import (
    ClaimIngestionUseCase,
    ClaimProfileDetectionUseCase,
    ClaimProfileRefinementUseCase,
    ClaimProfileTranslationUseCase,
    CompleteIngestionUseCase,
    CompleteProfileDetectionUseCase,
    CompleteProfileRefinementUseCase,
    CompleteProfileTranslationUseCase,
    FailIngestionUseCase,
    GetCandidateProfileUseCase,
    IngestCandidateProfileUseCase,
    SubmitRawTextUseCase,
)
from core.usecases.refinement import (
    ClaimRefinementJobUseCase,
    CompleteRefinementUseCase,
    FailRefinementUseCase,
)
from core.usecases.status import GetDatabaseStatusUseCase
from core.usecases.translation import (
    ClaimTranslationJobUseCase,
    CompleteTranslationUseCase,
    FailTranslationUseCase,
)

__all__ = [
    "CheckKnownUrlsUseCase",
    "ClaimDetectionJobUseCase",
    "ClaimIngestionUseCase",
    "ClaimMatchExplanationUseCase",
    "ClaimMatchingTaskUseCase",
    "ClaimProfileDetectionUseCase",
    "ClaimProfileRefinementUseCase",
    "ClaimProfileTranslationUseCase",
    "ClaimRefinementJobUseCase",
    "ClaimTranslationJobUseCase",
    "CompleteDetectionUseCase",
    "CompleteIngestionUseCase",
    "CompleteMatchExplanationUseCase",
    "CompleteProfileDetectionUseCase",
    "CompleteProfileRefinementUseCase",
    "CompleteProfileTranslationUseCase",
    "CompleteRefinementUseCase",
    "CompleteTranslationUseCase",
    "CreateJobsUseCase",
    "FailDetectionUseCase",
    "FailIngestionUseCase",
    "FailMatchExplanationUseCase",
    "FailMatchingTaskUseCase",
    "FailRefinementUseCase",
    "FailTranslationUseCase",
    "GetCandidateMatchesUseCase",
    "GetCandidateProfileUseCase",
    "GetDatabaseStatusUseCase",
    "GetPendingDetailsUseCase",
    "IngestCandidateProfileUseCase",
    "SubmitRawTextUseCase",
    "SubmitTaskMatchesUseCase",
    "UpdateJobDetailsUseCase",
]
