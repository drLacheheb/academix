from datetime import datetime, timezone
from sqlalchemy import update
from core.domain.interfaces.db import BaseMatchingQueueRepository
from core.domain.models.matching_task import MatchingTask
from core.infrastructure.db.models import MatchingQueueModel


class MatchingQueueRepository(BaseMatchingQueueRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def enqueue(self, entity_type: str, entity_id: str) -> None:
        session = self._SessionLocal()
        try:
            # Check if this task already exists in pending/claimed state
            existing = (
                session.query(MatchingQueueModel)
                .filter(
                    MatchingQueueModel.entity_type == entity_type,
                    MatchingQueueModel.entity_id == entity_id,
                    MatchingQueueModel.status.in_(["pending", "claimed"]),
                )
                .first()
            )
            if not existing:
                task = MatchingQueueModel(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    status="pending",
                )
                session.add(task)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next(self, agent_name: str, stale_cutoff: datetime) -> MatchingTask | None:
        session = self._SessionLocal()
        try:
            # Recover stale tasks
            session.execute(
                update(MatchingQueueModel)
                .where(
                    MatchingQueueModel.status == "claimed",
                    MatchingQueueModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="pending",
                    claimed_at=None,
                    claimed_by=None,
                )
            )

            # Find next pending task
            candidate = (
                session.query(MatchingQueueModel)
                .filter(MatchingQueueModel.status == "pending")
                .first()
            )
            if not candidate:
                session.commit()
                return None

            # Claim the task
            result = session.execute(
                update(MatchingQueueModel)
                .where(
                    MatchingQueueModel.id == candidate.id,
                    MatchingQueueModel.status == "pending",
                )
                .values(
                    status="claimed",
                    claimed_by=agent_name,
                    claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            session.commit()

            if result.rowcount == 1:
                return MatchingTask(
                    id=candidate.id,
                    entity_type=candidate.entity_type,
                    entity_id=candidate.entity_id,
                    status="claimed",
                    claimed_by=agent_name,
                    claimed_at=candidate.claimed_at,
                    created_at=candidate.created_at,
                )
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete(self, task_id: int) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(MatchingQueueModel)
                .where(MatchingQueueModel.id == task_id)
                .values(
                    status="completed",
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

    def fail(self, task_id: int) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(MatchingQueueModel)
                .where(MatchingQueueModel.id == task_id)
                .values(
                    status="failed",
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
                update(MatchingQueueModel)
                .where(
                    MatchingQueueModel.status == "claimed",
                    MatchingQueueModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="pending",
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
