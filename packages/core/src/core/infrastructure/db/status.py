from sqlalchemy.orm import sessionmaker

from core.domain.constants import JobStatus
from core.domain.interfaces.db import BaseStatusQueryRepository
from core.infrastructure.db.models import JobModel, JobOrchestrationModel


class StatusQueryRepository(BaseStatusQueryRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def get_status(self) -> dict:
        session = self._session_factory()
        try:
            total = session.query(JobModel).count()
            pending_details = session.query(JobModel).filter(JobModel.job_details.is_(None)).count()

            # Translation stats
            pending_translate = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.translation_status == JobStatus.PENDING)
                .count()
            )
            claimed_translate = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.translation_status == JobStatus.CLAIMED)
                .count()
            )
            completed_translate = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.translation_status == JobStatus.COMPLETED)
                .count()
            )
            skipped_translate = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.translation_status == JobStatus.SKIPPED)
                .count()
            )
            failed_translate = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.translation_status == JobStatus.FAILED)
                .count()
            )

            # Refinement stats
            pending_refine = (
                session.query(JobOrchestrationModel)
                .filter(
                    JobOrchestrationModel.refinement_status == JobStatus.PENDING,
                    JobOrchestrationModel.translation_status.in_(
                        [JobStatus.COMPLETED, JobStatus.SKIPPED]
                    ),
                )
                .count()
            )
            claimed_refine = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.refinement_status == JobStatus.CLAIMED)
                .count()
            )
            completed_refine = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.refinement_status == JobStatus.COMPLETED)
                .count()
            )
            failed_refine = (
                session.query(JobOrchestrationModel)
                .filter(JobOrchestrationModel.refinement_status == JobStatus.FAILED)
                .count()
            )

            return {
                "total_jobs": total,
                "pending_details": pending_details,
                "pending_translation": pending_translate,
                "claimed_translation": claimed_translate,
                "completed_translation": completed_translate,
                "skipped_translation": skipped_translate,
                "failed_translation": failed_translate,
                "pending_refinement": pending_refine,
                "claimed_refinement": claimed_refine,
                "completed_refinement": completed_refine,
                "failed_refinement": failed_refine,
            }
        finally:
            session.close()
