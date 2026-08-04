import json
from datetime import UTC, datetime

from sqlalchemy import update

from core.domain.constants import JobStatus
from core.domain.interfaces.db import BaseEmbeddingRepository
from core.domain.models.job import Job
from core.infrastructure.db.models import JobModel, JobOrchestrationModel


class EmbeddingRepository(BaseEmbeddingRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> Job | None:
        session = self._SessionLocal()
        try:
            # Recover stale embedding claims
            session.execute(
                update(JobOrchestrationModel)
                .where(
                    JobOrchestrationModel.embedding_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.embedding_claimed_at < stale_cutoff,
                )
                .values(
                    embedding_status=JobStatus.PENDING,
                    embedding_claimed_at=None,
                    embedding_claimed_by=None,
                )
            )

            candidate = (
                session.query(JobModel)
                .join(JobOrchestrationModel, JobModel.url == JobOrchestrationModel.job_url)
                .filter(
                    JobOrchestrationModel.refinement_status == JobStatus.COMPLETED,
                    JobOrchestrationModel.embedding_status == JobStatus.PENDING,
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
                    JobOrchestrationModel.embedding_status == JobStatus.PENDING,
                )
                .values(
                    embedding_status=JobStatus.CLAIMED,
                    embedding_claimed_by=agent_name,
                    embedding_claimed_at=datetime.now(UTC).replace(tzinfo=None),
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
        skill_embedding: list[float] | None = None,
        research_embedding: list[float] | None = None,
        degree_embedding: list[float] | None = None,
    ) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    skill_embedding=json.dumps(skill_embedding, ensure_ascii=False)
                    if skill_embedding is not None
                    else None,
                    research_embedding=json.dumps(research_embedding, ensure_ascii=False)
                    if research_embedding is not None
                    else None,
                    degree_embedding=json.dumps(degree_embedding, ensure_ascii=False)
                    if degree_embedding is not None
                    else None,
                )
            )
            session.execute(
                update(JobOrchestrationModel)
                .where(JobOrchestrationModel.job_url == url)
                .values(
                    embedding_status=JobStatus.COMPLETED,
                    embedding_claimed_by=None,
                    embedding_claimed_at=None,
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
                    embedding_status=JobStatus.FAILED,
                    embedding_claimed_by=None,
                    embedding_claimed_at=None,
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
                    JobOrchestrationModel.embedding_status == JobStatus.CLAIMED,
                    JobOrchestrationModel.embedding_claimed_at < stale_cutoff,
                )
                .values(
                    embedding_status=JobStatus.PENDING,
                    embedding_claimed_at=None,
                    embedding_claimed_by=None,
                )
            )
            session.commit()
            return result.rowcount
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
