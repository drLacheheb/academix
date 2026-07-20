import json
from core.utils.text import strip_accents
from datetime import datetime, timezone
from sqlalchemy import update

from core.domain.interfaces.db import BaseRefinementRepository
from core.domain.models.job import Job
from core.domain.constants import JobStatus
from core.infrastructure.db.models import JobModel, JobOrchestrationModel


class RefinementRepository(BaseRefinementRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        session = self._SessionLocal()
        try:
            # Recover stale claims for refinement specifically
            session.execute(
                update(JobOrchestrationModel)
                .where(
                    JobOrchestrationModel.refinement_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.claimed_at < stale_cutoff,
                )
                .values(
                    refinement_status=JobStatus.PENDING,
                    claimed_at=None,
                    claimed_by=None,
                )
            )

            candidate = (
                session.query(JobModel)
                .join(
                    JobOrchestrationModel, JobModel.url == JobOrchestrationModel.job_url
                )
                .filter(
                    JobModel.description.isnot(None),
                    JobOrchestrationModel.refinement_status == JobStatus.PENDING,
                    JobOrchestrationModel.translation_status.in_(
                        [JobStatus.COMPLETED, JobStatus.SKIPPED]
                    ),
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
                    JobOrchestrationModel.refinement_status == JobStatus.PENDING,
                )
                .values(
                    refinement_status=JobStatus.CLAIMED,
                    claimed_by=agent_name,
                    claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
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

    def complete(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        session = self._SessionLocal()
        try:
            job_model = session.query(JobModel).filter(JobModel.url == url).first()
            if not job_model:
                raise ValueError(f"Job not found for url: {url}")

            skills_str = (
                json.dumps([strip_accents(s) for s in required_skills if s])
                if required_skills is not None
                else None
            )
            # Update job metadata
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    required_skills=skills_str,
                    education_level=strip_accents(education_level),
                    city=strip_accents(city),
                    country=strip_accents(country),
                    skill_embedding=json.dumps(skill_embedding)
                    if skill_embedding is not None
                    else None,
                    research_embedding=json.dumps(research_embedding)
                    if research_embedding is not None
                    else None,
                )
            )
            # Update refinement orchestration statuses
            session.execute(
                update(JobOrchestrationModel)
                .where(JobOrchestrationModel.job_url == url)
                .values(
                    refinement_status=JobStatus.COMPLETED,
                    claimed_by=None,
                    claimed_at=None,
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
                    refinement_status=JobStatus.FAILED,
                    claimed_by=None,
                    claimed_at=None,
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
                    JobOrchestrationModel.refinement_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.claimed_at < stale_cutoff,
                )
                .values(
                    refinement_status=JobStatus.PENDING,
                    claimed_at=None,
                    claimed_by=None,
                )
            )
            session.commit()
            return result.rowcount
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
