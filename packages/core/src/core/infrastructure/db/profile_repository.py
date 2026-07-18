import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update
from core.domain.interfaces.db import BaseCandidateProfileRepository
from core.domain.models.profile import CandidateProfile
from core.infrastructure.db.models import CandidateProfileModel


class DatabaseCandidateProfileRepository(BaseCandidateProfileRepository):
    def __init__(self, database_url_or_session_factory):
        if isinstance(database_url_or_session_factory, str):
            if database_url_or_session_factory.startswith("sqlite"):
                engine = create_engine(database_url_or_session_factory, echo=False, connect_args={"timeout": 30})
            else:
                engine = create_engine(database_url_or_session_factory, echo=False)
            self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        else:
            self._SessionLocal = database_url_or_session_factory

    def save(self, profile: CandidateProfile) -> CandidateProfile:
        session = self._SessionLocal()
        try:
            model = CandidateProfileModel.from_domain(profile)
            if model.id:
                existing = session.query(CandidateProfileModel).filter(CandidateProfileModel.id == model.id).first()
                if existing:
                    existing.name = model.name
                    existing.email = model.email
                    existing.cv_file_path = model.cv_file_path
                    existing.raw_text = model.raw_text
                    existing.highest_degree = model.highest_degree
                    existing.skills = model.skills
                    existing.languages = model.languages
                    existing.experience = model.experience
                    existing.preferred_locations = model.preferred_locations
                    existing.research_interests = model.research_interests
                    existing.status = model.status
                    existing.status_message = model.status_message
                    existing.claimed_by = model.claimed_by
                    existing.claimed_at = model.claimed_at
                    model = existing
                else:
                    session.add(model)
            else:
                existing = None
                if model.email:
                    existing = session.query(CandidateProfileModel).filter(CandidateProfileModel.email == model.email).first()
                
                if existing:
                    existing.name = model.name
                    existing.cv_file_path = model.cv_file_path
                    existing.raw_text = model.raw_text
                    existing.highest_degree = model.highest_degree
                    existing.skills = model.skills
                    existing.languages = model.languages
                    existing.experience = model.experience
                    existing.preferred_locations = model.preferred_locations
                    existing.research_interests = model.research_interests
                    existing.status = model.status
                    existing.status_message = model.status_message
                    existing.claimed_by = model.claimed_by
                    existing.claimed_at = model.claimed_at
                    model = existing
                else:
                    session.add(model)
            session.commit()
            session.refresh(model)
            return model.to_domain()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_by_id(self, profile_id: int) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            model = session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
            return model.to_domain() if model else None
        finally:
            session.close()

    def get_by_email(self, email: str) -> CandidateProfile | None:
        if not email:
            return None
        session = self._SessionLocal()
        try:
            model = session.query(CandidateProfileModel).filter(CandidateProfileModel.email == email).first()
            return model.to_domain() if model else None
        finally:
            session.close()

    def get_all(self) -> list[CandidateProfile]:
        session = self._SessionLocal()
        try:
            models = session.query(CandidateProfileModel).all()
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def claim_next_for_ingestion(self, agent_name: str, stale_cutoff: datetime) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            # 1. Recover stale claims
            session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.status == "INGESTING",
                    CandidateProfileModel.claimed_at < stale_cutoff,
                )
                .values(
                    claimed_by=None,
                    claimed_at=None,
                )
            )

            # 2. Find next task (status is INGESTING and claimed_by is None)
            candidate = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.status == "INGESTING",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            # 3. Safe CAS claim
            result = session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.id == candidate.id,
                    CandidateProfileModel.status == "INGESTING",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .values(
                    claimed_by=agent_name,
                    claimed_at=datetime.now(),
                    status_message="Claimed by CV parsing worker...",
                )
            )
            session.commit()

            if result.rowcount > 0:
                session.refresh(candidate)
                return candidate.to_domain()
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_ingestion(self, profile_id: int, profile: CandidateProfile) -> None:
        session = self._SessionLocal()
        try:
            existing = session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
            if existing:
                existing.name = profile.name
                existing.email = profile.email
                existing.cv_file_path = profile.cv_file_path
                existing.raw_text = profile.raw_text
                existing.highest_degree = profile.highest_degree
                existing.skills = json.dumps(profile.skills) if profile.skills else None
                existing.languages = json.dumps(profile.languages) if profile.languages else None
                existing.experience = json.dumps(profile.experience) if profile.experience else None
                existing.preferred_locations = json.dumps(profile.preferred_locations) if profile.preferred_locations else None
                existing.research_interests = json.dumps(profile.research_interests) if profile.research_interests else None
                existing.skill_embedding = json.dumps(profile.skill_embedding) if profile.skill_embedding else None
                existing.research_embedding = json.dumps(profile.research_embedding) if profile.research_embedding else None
                existing.status = "COMPLETED"
                existing.status_message = "Parsed successfully"
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_ingestion(self, profile_id: int, error_message: str) -> None:
        session = self._SessionLocal()
        try:
            existing = session.query(CandidateProfileModel).filter(CandidateProfileModel.id == profile_id).first()
            if existing:
                existing.status = "FAILED"
                existing.status_message = error_message
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
