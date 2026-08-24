from core.domain.models.schemas import JobStubCreate
from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from core.usecases.check_known_urls import CheckKnownUrlsUseCase
from core.usecases.create_jobs import CreateJobsUseCase
from core.usecases.details import UpdateJobDetailsUseCase
from core.usecases.status import GetDatabaseStatusUseCase
from core.usecases.translation import ClaimTranslationJobUseCase, CompleteTranslationUseCase


def test_create_jobs_usecase(memory_repo: PipelineJobRepository):
    create_uc = CreateJobsUseCase(memory_repo)
    stubs = [
        JobStubCreate(title="PhD Quantum", url="https://example.com/1", source="abg"),
        JobStubCreate(title="PhD Optics", url="https://example.com/2", source="euraxess"),
    ]
    count = create_uc.execute(stubs)
    assert count == 2

    # Check known URLs
    check_uc = CheckKnownUrlsUseCase(memory_repo)
    known = check_uc.execute(["https://example.com/1", "https://example.com/3"])
    assert "https://example.com/1" in known
    assert "https://example.com/3" not in known


def test_update_details_usecase(memory_repo: PipelineJobRepository):
    from core.domain.models.schemas import JobDetailUpdate

    create_uc = CreateJobsUseCase(memory_repo)
    create_uc.execute(
        [JobStubCreate(title="PhD Quantum", url="https://example.com/10", source="abg")]
    )

    update_uc = UpdateJobDetailsUseCase(memory_repo)
    update_uc.execute(
        [
            JobDetailUpdate(
                url="https://example.com/10",
                job_details="Detailed description of quantum thesis.",
            )
        ]
    )

    # Claim translation
    claim_uc = ClaimTranslationJobUseCase(memory_repo.translation)
    job = claim_uc.execute("worker-1")
    assert job is not None
    assert job.url == "https://example.com/10"
    assert job.job_details == "Detailed description of quantum thesis."

    # Complete translation
    complete_uc = CompleteTranslationUseCase(memory_repo.translation)
    complete_uc.execute("https://example.com/10", "Translated English description.")


def test_status_usecase(memory_repo: PipelineJobRepository):
    create_uc = CreateJobsUseCase(memory_repo)
    create_uc.execute([JobStubCreate(title="Job A", url="https://example.com/a", source="abg")])

    status_uc = GetDatabaseStatusUseCase(memory_repo.status)
    status = status_uc.execute()
    assert "total_jobs" in status
    assert status["total_jobs"] == 1
    assert "pending_translation" in status
