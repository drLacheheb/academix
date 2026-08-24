from core.domain.constants import JobStatus
from core.domain.models.job import Job
from core.infrastructure.db.models import JobModel, JobOrchestrationModel
from core.infrastructure.db.pipeline_repository import PipelineJobRepository


def test_save_and_retrieve_job(memory_repo: PipelineJobRepository, sample_job_en: Job):
    memory_repo.save([sample_job_en])

    session = memory_repo._SessionLocal()
    job = session.query(JobModel).filter(JobModel.url == sample_job_en.url).first()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_en.url)
        .first()
    )

    assert job is not None
    assert orch is not None
    assert job.title == sample_job_en.title
    assert job.job_details == sample_job_en.job_details
    assert orch.translation_status == JobStatus.PENDING
    assert orch.refinement_status == JobStatus.PENDING
    assert orch.embedding_status == JobStatus.PENDING
    session.close()


def test_deduplicate_job_urls(memory_repo: PipelineJobRepository, sample_job_en: Job):
    memory_repo.save([sample_job_en])
    # Duplicate save with same URL
    memory_repo.save([sample_job_en])

    session = memory_repo._SessionLocal()
    count = session.query(JobModel).filter(JobModel.url == sample_job_en.url).count()
    assert count == 1
    session.close()


def test_get_all_urls(memory_repo: PipelineJobRepository, sample_job_en: Job, sample_job_fr: Job):
    memory_repo.save([sample_job_en, sample_job_fr])
    urls = memory_repo.get_all_urls()
    assert sample_job_en.url in urls
    assert sample_job_fr.url in urls


def test_update_job_details(memory_repo: PipelineJobRepository):
    from core.domain.models.schemas import JobDetailUpdate

    stub_job = Job(
        title="Pending Job",
        url="https://example.com/pending-1",
        source="euraxess",
        job_details=None,
    )
    memory_repo.save([stub_job])

    # Sourcing scrapes the details and updates the job
    memory_repo.update_details(
        [
            JobDetailUpdate(
                url="https://example.com/pending-1",
                job_details="Scraped detailed content.",
            )
        ]
    )

    session = memory_repo._SessionLocal()
    updated = session.query(JobModel).filter(JobModel.url == stub_job.url).first()
    assert updated is not None
    assert updated.job_details == "Scraped detailed content."
    session.close()
