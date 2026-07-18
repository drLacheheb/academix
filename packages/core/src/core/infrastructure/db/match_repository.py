from datetime import datetime, timezone
from sqlalchemy import update, desc
from core.domain.interfaces.db import BaseMatchRepository
from core.domain.models.match import Match
from core.infrastructure.db.models import MatchModel


class MatchRepository(BaseMatchRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def save_matches(self, matches: list[Match]) -> None:
        session = self._SessionLocal()
        try:
            for match in matches:
                existing = (
                    session.query(MatchModel)
                    .filter(
                        MatchModel.candidate_id == match.candidate_id,
                        MatchModel.job_url == match.job_url,
                    )
                    .first()
                )
                if existing:
                    existing.score = match.score
                    existing.degree_eligible = match.degree_eligible
                    existing.language_eligible = match.language_eligible
                    existing.skill_score = match.skill_score
                    existing.research_score = match.research_score
                    existing.explanation = None
                    existing.explanation_status = "pending"
                    existing.explanation_claimed_by = None
                    existing.explanation_claimed_at = None
                else:
                    model = MatchModel(
                        candidate_id=match.candidate_id,
                        job_url=match.job_url,
                        score=match.score,
                        degree_eligible=match.degree_eligible,
                        language_eligible=match.language_eligible,
                        skill_score=match.skill_score,
                        research_score=match.research_score,
                        explanation=None,
                        explanation_status="pending",
                    )
                    session.add(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_matches_for_candidate(self, candidate_id: int, limit: int = 20) -> list[Match]:
        session = self._SessionLocal()
        try:
            models = (
                session.query(MatchModel)
                .filter(MatchModel.candidate_id == candidate_id)
                .order_by(desc(MatchModel.score))
                .limit(limit)
                .all()
            )
            return [model.to_domain() for model in models]
        finally:
            session.close()

    def exists(self, candidate_id: int, job_url: str) -> bool:
        session = self._SessionLocal()
        try:
            count = (
                session.query(MatchModel)
                .filter(
                    MatchModel.candidate_id == candidate_id,
                    MatchModel.job_url == job_url,
                )
                .count()
            )
            return count > 0
        finally:
            session.close()

    def claim_next_pending_explanation(self, agent_name: str, stale_cutoff: datetime, threshold: float = 0.3) -> Match | None:
        session = self._SessionLocal()
        try:
            # Recover stale claims
            session.execute(
                update(MatchModel)
                .where(
                    MatchModel.explanation_status == "claimed",
                    MatchModel.explanation_claimed_at < stale_cutoff,
                )
                .values(
                    explanation_status="pending",
                    explanation_claimed_by=None,
                    explanation_claimed_at=None,
                )
            )

            # Find next pending match that qualifies (score >= threshold)
            candidate = (
                session.query(MatchModel)
                .filter(
                    MatchModel.explanation_status == "pending",
                    MatchModel.score >= threshold,
                )
                .order_by(desc(MatchModel.score))
                .first()
            )
            if not candidate:
                session.commit()
                return None

            # Claim it
            result = session.execute(
                update(MatchModel)
                .where(
                    MatchModel.id == candidate.id,
                    MatchModel.explanation_status == "pending",
                )
                .values(
                    explanation_status="claimed",
                    explanation_claimed_by=agent_name,
                    explanation_claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
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

    def complete_explanation(self, match_id: int, explanation: str) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(MatchModel)
                .where(MatchModel.id == match_id)
                .values(
                    explanation=explanation,
                    explanation_status="completed",
                    explanation_claimed_by=None,
                    explanation_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_explanation(self, match_id: int) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(MatchModel)
                .where(MatchModel.id == match_id)
                .values(
                    explanation_status="failed",
                    explanation_claimed_by=None,
                    explanation_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def recover_stale_explanations(self, stale_cutoff: datetime) -> int:
        session = self._SessionLocal()
        try:
            result = session.execute(
                update(MatchModel)
                .where(
                    MatchModel.explanation_status == "claimed",
                    MatchModel.explanation_claimed_at < stale_cutoff,
                )
                .values(
                    explanation_status="pending",
                    explanation_claimed_by=None,
                    explanation_claimed_at=None,
                )
            )
            session.commit()
            return result.rowcount
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
