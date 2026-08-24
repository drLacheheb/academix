from datetime import datetime, timedelta

from core.domain.constants import JobStatus
from core.domain.models.job import Job
from core.infrastructure.db.models import JobModel, JobOrchestrationModel
from core.infrastructure.db.pipeline_repository import PipelineJobRepository


def test_claim_translation_job(memory_repo: PipelineJobRepository, sample_job_fr: Job):
    memory_repo.save([sample_job_fr])
    claimed = memory_repo.claim_next_for_translation("worker-1")

    assert claimed is not None
    assert claimed.url == sample_job_fr.url

    session = memory_repo._SessionLocal()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_fr.url)
        .first()
    )
    assert orch is not None
    assert orch.translation_status == JobStatus.CLAIMED
    assert orch.translation_claimed_by == "worker-1"
    assert orch.translation_claimed_at is not None
    session.close()


def test_complete_translation_with_translated_content(
    memory_repo: PipelineJobRepository, sample_job_fr: Job
):
    memory_repo.save([sample_job_fr])
    memory_repo.claim_next_for_translation("worker-1")

    memory_repo.complete_translation(
        url=sample_job_fr.url,
        job_details_en="## Description of the subject\n\nTranslated English text.",
    )

    session = memory_repo._SessionLocal()
    job = session.query(JobModel).filter(JobModel.url == sample_job_fr.url).first()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_fr.url)
        .first()
    )

    assert job is not None and orch is not None
    assert job.job_details_en == "## Description of the subject\n\nTranslated English text."
    assert orch.translation_status == JobStatus.COMPLETED
    assert orch.refinement_status == JobStatus.PENDING
    session.close()


def test_complete_translation_with_none_skips_translation(
    memory_repo: PipelineJobRepository, sample_job_en: Job
):
    memory_repo.save([sample_job_en])
    memory_repo.claim_next_for_translation("worker-1")

    memory_repo.complete_translation(
        url=sample_job_en.url,
        job_details_en=None,
    )

    session = memory_repo._SessionLocal()
    job = session.query(JobModel).filter(JobModel.url == sample_job_en.url).first()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_en.url)
        .first()
    )

    assert job is not None and orch is not None
    assert job.job_details_en is None
    assert orch.translation_status == JobStatus.SKIPPED
    assert orch.refinement_status == JobStatus.PENDING
    session.close()


def test_fail_translation(memory_repo: PipelineJobRepository, sample_job_fr: Job):
    memory_repo.save([sample_job_fr])
    memory_repo.claim_next_for_translation("worker-1")
    memory_repo.fail_translation(sample_job_fr.url)

    session = memory_repo._SessionLocal()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_fr.url)
        .first()
    )
    assert orch is not None
    assert orch.translation_status == JobStatus.FAILED
    session.close()


def test_stale_claim_recovery(memory_repo: PipelineJobRepository, sample_job_fr: Job):
    memory_repo.save([sample_job_fr])
    memory_repo.claim_next_for_translation("worker-1")

    from datetime import UTC

    # Manually set claim time to 30 minutes in the past in UTC
    session = memory_repo._SessionLocal()
    orch = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_fr.url)
        .first()
    )
    assert orch is not None
    orch.translation_claimed_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=30)
    session.commit()
    session.close()

    # Recover stale claims
    recovered = memory_repo.recover_stale_claims()
    assert recovered >= 1

    session = memory_repo._SessionLocal()
    orch_after = (
        session.query(JobOrchestrationModel)
        .filter(JobOrchestrationModel.job_url == sample_job_fr.url)
        .first()
    )
    assert orch_after is not None
    assert orch_after.translation_status == JobStatus.PENDING
    assert orch_after.translation_claimed_by is None
    session.close()
