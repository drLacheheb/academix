from datetime import datetime, timezone
from sqlalchemy import update

from core.domain.interfaces.db import BaseTranslationRepository
from core.domain.models.job import Job
from core.domain.constants import JobStatus
from core.infrastructure.db.models import JobModel


class TranslationRepository(BaseTranslationRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        session = self._SessionLocal()
        try:
            # Recover stale claims for translation specifically
            session.execute(
                update(JobModel)
                .where(
                    JobModel.translation_status == JobStatus.CLAIMED,
                    JobModel.translation_claimed_at < stale_cutoff,
                )
                .values(
                    translation_status=JobStatus.PENDING,
                    translation_claimed_at=None,
                    translation_claimed_by=None,
                )
            )

            candidate = (
                session.query(JobModel)
                .filter(
                    JobModel.translation_status == JobStatus.PENDING,
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(JobModel)
                .where(
                    JobModel.id == candidate.id,
                    JobModel.translation_status == JobStatus.PENDING,
                )
                .values(
                    translation_status=JobStatus.CLAIMED,
                    translation_claimed_by=agent_name,
                    translation_claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
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

    def complete(self, url: str, description_en: str | None, requirements_en: str | None) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    description_en=description_en,
                    requirements_en=requirements_en,
                    translation_status=JobStatus.COMPLETED,
                    translation_claimed_by=None,
                    translation_claimed_at=None,
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
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    translation_status=JobStatus.FAILED,
                    translation_claimed_by=None,
                    translation_claimed_at=None,
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
                update(JobModel)
                .where(
                    JobModel.translation_status == JobStatus.CLAIMED,
                    JobModel.translation_claimed_at < stale_cutoff,
                )
                .values(
                    translation_status=JobStatus.PENDING,
                    translation_claimed_at=None,
                    translation_claimed_by=None,
                )
            )
            session.commit()
            return result.rowcount
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
