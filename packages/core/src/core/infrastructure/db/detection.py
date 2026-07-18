from datetime import datetime, timezone
from sqlalchemy import update

from core.domain.interfaces.db import BaseDetectionRepository
from core.domain.models.job import Job
from core.domain.constants import JobStatus
from core.infrastructure.db.models import JobModel, JobOrchestrationModel


class LanguageDetectionRepository(BaseDetectionRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        session = self._SessionLocal()
        try:
            # Recover stale claims for detection specifically
            session.execute(
                update(JobOrchestrationModel)
                .where(
                    JobOrchestrationModel.detection_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.detection_claimed_at < stale_cutoff,
                )
                .values(
                    detection_status=JobStatus.PENDING,
                    detection_claimed_at=None,
                    detection_claimed_by=None,
                )
            )

            candidate = (
                session.query(JobModel)
                .join(JobOrchestrationModel, JobModel.url == JobOrchestrationModel.job_url)
                .filter(
                    JobModel.description.isnot(None),
                    JobOrchestrationModel.detection_status == JobStatus.PENDING,
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(JobOrchestrationModel)
                .where(
                    JobOrchestrationModel.job_url == candidate.url,
                    JobOrchestrationModel.detection_status == JobStatus.PENDING,
                )
                .values(
                    detection_status=JobStatus.CLAIMED,
                    detection_claimed_by=agent_name,
                    detection_claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            session.commit()

            if result.rowcount == 1:
                return candidate.to_domain()
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete(self, url: str, language_code: str) -> None:
        session = self._SessionLocal()
        try:
            # Update job language code
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(language_code=language_code)
            )
            # Update orchestration statuses
            translation_status = (
                JobStatus.SKIPPED if language_code == "en" else JobStatus.PENDING
            )
            session.execute(
                update(JobOrchestrationModel)
                .where(JobOrchestrationModel.job_url == url)
                .values(
                    detection_status=JobStatus.COMPLETED,
                    detection_claimed_by=None,
                    detection_claimed_at=None,
                    translation_status=translation_status,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail(self, url: str) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobOrchestrationModel)
                .where(JobOrchestrationModel.job_url == url)
                .values(
                    detection_status=JobStatus.FAILED,
                    detection_claimed_by=None,
                    detection_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def recover_stale(self, stale_cutoff: datetime) -> int:
        session = self._SessionLocal()
        try:
            result = session.execute(
                update(JobOrchestrationModel)
                .where(
                    JobOrchestrationModel.detection_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.detection_claimed_at < stale_cutoff,
                )
                .values(
                    detection_status=JobStatus.PENDING,
                    detection_claimed_at=None,
                    detection_claimed_by=None,
                )
            )
            session.commit()
            return result.rowcount
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
