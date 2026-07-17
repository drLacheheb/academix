from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
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
                    model = existing
                else:
                    session.add(model)
            else:
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
        session = self._SessionLocal()
        try:
            model = session.query(CandidateProfileModel).filter(CandidateProfileModel.email == email).first()
            return model.to_domain() if model else None
        finally:
            session.close()
