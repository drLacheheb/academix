from datetime import UTC, datetime

from sqlalchemy import desc, update

from core.domain.interfaces.db import BaseMatchRepository
from core.domain.models.match import Match
from core.infrastructure.db.models import MatchModel


class MatchRepository(BaseMatchRepository):
    def __init__(self, session_factory):
        self._SessionLocal = session_factory

    def save_matches(self, matches: list[Match]) -> None:
        import os

        enable_explanations = os.environ.get("ENABLE_MATCH_EXPLANATION", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        initial_status = "pending" if enable_explanations else "skipped"

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
                    existing.explanation = match.explanation
                    existing.explanation_status = initial_status
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
                        explanation=match.explanation,
                        explanation_status=initial_status,
                    )
                    session.add(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_matches_for_candidate(self, candidate_id: int, limit: int = 20) -> list[Match]:
        from core.infrastructure.db.models import JobModel

        session = self._SessionLocal()
        try:
            results = (
                session.query(MatchModel, JobModel)
                .join(JobModel, MatchModel.job_url == JobModel.url)
                .filter(MatchModel.candidate_id == candidate_id)
                .order_by(desc(MatchModel.score))
                .limit(limit)
                .all()
            )
            matches = []
            for model, job in results:
                domain_match = model.to_domain()
                domain_match.job_title = job.title
                domain_match.employer = job.employer
                domain_match.deadline = job.deadline
                domain_match.job_degree_fields = job.degree_fields
                matches.append(domain_match)
            return matches
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

    def claim_next_pending_explanation(
        self, agent_name: str, stale_cutoff: datetime, threshold: float = 0.3
    ) -> Match | None:
        session = self._SessionLocal()
        try:
            match = (
                session.query(MatchModel)
                .filter(
                    MatchModel.score >= threshold,
                    MatchModel.explanation_status == "pending",
                    (MatchModel.explanation_claimed_at.is_(None))
                    | (MatchModel.explanation_claimed_at < stale_cutoff),
                )
                .order_by(desc(MatchModel.score))
                .with_for_update(skip_locked=True)
                .first()
            )

            if not match:
                return None

            match.explanation_claimed_by = agent_name
            match.explanation_claimed_at = datetime.now(UTC).replace(tzinfo=None)
            session.commit()
            return match.to_domain()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_explanation(self, match_id: int, explanation: str) -> None:
        session = self._SessionLocal()
        try:
            match = session.query(MatchModel).filter(MatchModel.id == match_id).first()
            if match:
                match.explanation = explanation
                match.explanation_status = "completed"
                match.explanation_claimed_by = None
                match.explanation_claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_explanation(self, match_id: int) -> None:
        session = self._SessionLocal()
        try:
            match = session.query(MatchModel).filter(MatchModel.id == match_id).first()
            if match:
                match.explanation_status = "failed"
                match.explanation_claimed_by = None
                match.explanation_claimed_at = None
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

    def get_unnotified_matches(self, limit: int = 10) -> list[dict]:
        from core.infrastructure.db.models import CandidateProfileModel, JobModel

        session = self._SessionLocal()
        try:
            results = (
                session.query(MatchModel, JobModel, CandidateProfileModel)
                .join(JobModel, MatchModel.job_url == JobModel.url)
                .join(CandidateProfileModel, MatchModel.candidate_id == CandidateProfileModel.id)
                .filter(
                    MatchModel.telegram_notified == False,  # noqa: E712
                    MatchModel.explanation_status.in_(["completed", "skipped"]),
                    CandidateProfileModel.telegram_chat_id.isnot(None),
                )
                .order_by(desc(MatchModel.score))
                .limit(limit)
                .all()
            )
            unnotified = []
            for match, job, profile in results:
                unnotified.append(
                    {
                        "match_id": match.id,
                        "candidate_id": match.candidate_id,
                        "telegram_chat_id": profile.telegram_chat_id,
                        "job_url": match.job_url,
                        "score": match.score,
                        "job_title": job.title,
                        "employer": job.employer,
                        "city": job.city,
                        "country": job.country,
                        "deadline": job.deadline,
                        "degree_fields": job.degree_fields,
                        "explanation": match.explanation or "Matching criteria satisfied.",
                    }
                )
            return unnotified
        finally:
            session.close()

    def mark_as_notified(self, match_ids: list[int]) -> None:
        if not match_ids:
            return
        session = self._SessionLocal()
        try:
            session.execute(
                update(MatchModel)
                .where(MatchModel.id.in_(match_ids))
                .values(
                    telegram_notified=True,
                    telegram_notified_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
