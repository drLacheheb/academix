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
                engine = create_engine(
                    database_url_or_session_factory,
                    echo=False,
                    connect_args={"timeout": 30},
                )
            else:
                engine = create_engine(database_url_or_session_factory, echo=False)
            self._SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
        else:
            self._SessionLocal = database_url_or_session_factory

    def save(self, profile: CandidateProfile) -> CandidateProfile:
        session = self._SessionLocal()
        try:
            model = CandidateProfileModel.from_domain(profile)
            if model.id:
                existing = (
                    session.query(CandidateProfileModel)
                    .filter(CandidateProfileModel.id == model.id)
                    .first()
                )
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
                    existing = (
                        session.query(CandidateProfileModel)
                        .filter(CandidateProfileModel.email == model.email)
                        .first()
                    )

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
            model = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            return model.to_domain() if model else None
        finally:
            session.close()

    def get_by_email(self, email: str) -> CandidateProfile | None:
        if not email:
            return None
        session = self._SessionLocal()
        try:
            model = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.email == email)
                .first()
            )
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

    def claim_next_for_ingestion(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
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
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                existing.name = profile.name
                existing.email = profile.email
                existing.cv_file_path = profile.cv_file_path
                existing.raw_text = profile.raw_text
                existing.highest_degree = profile.highest_degree
                existing.skills = json.dumps(profile.skills, ensure_ascii=False) if profile.skills else None
                existing.languages = (
                    json.dumps(profile.languages, ensure_ascii=False) if profile.languages else None
                )
                existing.experience = (
                    json.dumps(profile.experience, ensure_ascii=False) if profile.experience else None
                )
                existing.preferred_locations = (
                    json.dumps(profile.preferred_locations, ensure_ascii=False)
                    if profile.preferred_locations
                    else None
                )
                existing.research_interests = (
                    json.dumps(profile.research_interests, ensure_ascii=False)
                    if profile.research_interests
                    else None
                )
                existing.skill_embedding = (
                    json.dumps(profile.skill_embedding, ensure_ascii=False)
                    if profile.skill_embedding
                    else None
                )
                existing.research_embedding = (
                    json.dumps(profile.research_embedding, ensure_ascii=False)
                    if profile.research_embedding
                    else None
                )
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
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
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

    def submit_raw_text(
        self,
        profile_id: int,
        raw_text: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                existing.raw_text = raw_text
                if name:
                    existing.name = name
                if email:
                    existing.email = email
                existing.status = "PENDING_DETECTION"
                existing.status_message = "Raw text parsed successfully"
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_detection(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.status == "DETECTION_CLAIMED",
                    CandidateProfileModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="PENDING_DETECTION",
                    claimed_by=None,
                    claimed_at=None,
                )
            )
            candidate = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.status == "PENDING_DETECTION",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.id == candidate.id,
                    CandidateProfileModel.status == "PENDING_DETECTION",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .values(
                    status="DETECTION_CLAIMED",
                    claimed_by=agent_name,
                    claimed_at=datetime.now(),
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

    def complete_detection(self, profile_id: int, language_code: str) -> None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                existing.language_code = language_code
                if language_code == "en":
                    existing.status = "PENDING_REFINEMENT"
                else:
                    existing.status = "PENDING_TRANSLATION"
                existing.status_message = f"Language detected: {language_code}"
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_translation(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.status == "TRANSLATION_CLAIMED",
                    CandidateProfileModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="PENDING_TRANSLATION",
                    claimed_by=None,
                    claimed_at=None,
                )
            )
            candidate = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.status == "PENDING_TRANSLATION",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.id == candidate.id,
                    CandidateProfileModel.status == "PENDING_TRANSLATION",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .values(
                    status="TRANSLATION_CLAIMED",
                    claimed_by=agent_name,
                    claimed_at=datetime.now(),
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

    def complete_translation(self, profile_id: int, raw_text_en: str) -> None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                existing.raw_text_en = raw_text_en
                existing.status = "PENDING_REFINEMENT"
                existing.status_message = "Translation completed"
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_refinement(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.status == "REFINEMENT_CLAIMED",
                    CandidateProfileModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="PENDING_REFINEMENT",
                    claimed_by=None,
                    claimed_at=None,
                )
            )
            candidate = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.status == "PENDING_REFINEMENT",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.id == candidate.id,
                    CandidateProfileModel.status == "PENDING_REFINEMENT",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .values(
                    status="REFINEMENT_CLAIMED",
                    claimed_by=agent_name,
                    claimed_at=datetime.now(),
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

    def complete_refinement(self, profile_id: int, profile: CandidateProfile) -> int:
        session = self._SessionLocal()
        try:
            # Check if there is another candidate with the same email
            existing_email = None
            if profile.email:
                existing_email = (
                    session.query(CandidateProfileModel)
                    .filter(
                        CandidateProfileModel.email == profile.email,
                        CandidateProfileModel.id != profile_id,
                    )
                    .first()
                )

            # Get the current placeholder
            placeholder = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )

            if existing_email:
                # Merge into the existing candidate profile
                if profile.name:
                    existing_email.name = profile.name
                existing_email.email = profile.email
                if placeholder:
                    existing_email.cv_file_path = placeholder.cv_file_path or existing_email.cv_file_path
                    existing_email.raw_text = placeholder.raw_text or existing_email.raw_text
                    existing_email.raw_text_en = placeholder.raw_text_en or existing_email.raw_text_en
                    existing_email.language_code = placeholder.language_code or existing_email.language_code
                existing_email.highest_degree = profile.highest_degree if profile.highest_degree else None
                existing_email.skills = (
                    json.dumps([s for s in profile.skills if s], ensure_ascii=False)
                    if profile.skills
                    else None
                )
                existing_email.languages = (
                    json.dumps(
                        [
                            {
                                "language": lang.get("language")
                                if isinstance(lang, dict)
                                else str(lang),
                                "proficiency": lang.get("proficiency")
                                if isinstance(lang, dict)
                                else None,
                            }
                            for lang in profile.languages
                            if lang
                        ],
                        ensure_ascii=False,
                    )
                    if profile.languages
                    else None
                )
                existing_email.experience = (
                    json.dumps(
                        [
                            {
                                "role": exp.get("role")
                                if isinstance(exp, dict)
                                else str(exp),
                                "organization": exp.get("organization")
                                if isinstance(exp, dict)
                                else None,
                                "from_date": exp.get("from_date")
                                if isinstance(exp, dict)
                                else None,
                                "to_date": exp.get("to_date")
                                if isinstance(exp, dict)
                                else None,
                                "description": exp.get("description")
                                if isinstance(exp, dict)
                                else None,
                            }
                            for exp in profile.experience
                            if exp
                        ],
                        ensure_ascii=False,
                    )
                    if profile.experience
                    else None
                )
                existing_email.preferred_locations = (
                    json.dumps([loc for loc in profile.preferred_locations if loc], ensure_ascii=False)
                    if profile.preferred_locations
                    else None
                )
                existing_email.research_interests = (
                    json.dumps([ri for ri in profile.research_interests if ri], ensure_ascii=False)
                    if profile.research_interests
                    else None
                )
                existing_email.skill_embedding = json.dumps(profile.skill_embedding, ensure_ascii=False) if profile.skill_embedding else None
                existing_email.research_embedding = json.dumps(profile.research_embedding, ensure_ascii=False) if profile.research_embedding else None
                existing_email.status = "COMPLETED"
                existing_email.status_message = "Updated successfully via newer CV upload"
                existing_email.claimed_by = None
                existing_email.claimed_at = None

                # Delete the temporary placeholder
                if placeholder:
                    session.delete(placeholder)
                
                session.commit()
                return existing_email.id
            else:
                # Normal update of the placeholder
                if placeholder:
                    if profile.name:
                        placeholder.name = profile.name
                    if profile.email:
                        placeholder.email = profile.email
                    placeholder.highest_degree = profile.highest_degree if profile.highest_degree else None
                    placeholder.skills = (
                        json.dumps([s for s in profile.skills if s], ensure_ascii=False)
                        if profile.skills
                        else None
                    )
                    placeholder.languages = (
                        json.dumps(
                            [
                                {
                                    "language": lang.get("language")
                                    if isinstance(lang, dict)
                                    else str(lang),
                                    "proficiency": lang.get("proficiency")
                                    if isinstance(lang, dict)
                                    else None,
                                }
                                for lang in profile.languages
                                if lang
                            ],
                            ensure_ascii=False,
                        )
                        if profile.languages
                        else None
                    )
                    placeholder.experience = (
                        json.dumps(
                            [
                                {
                                    "role": exp.get("role")
                                    if isinstance(exp, dict)
                                    else str(exp),
                                    "organization": exp.get("organization")
                                    if isinstance(exp, dict)
                                    else None,
                                    "from_date": exp.get("from_date")
                                    if isinstance(exp, dict)
                                    else None,
                                    "to_date": exp.get("to_date")
                                    if isinstance(exp, dict)
                                    else None,
                                    "description": exp.get("description")
                                    if isinstance(exp, dict)
                                    else None,
                                }
                                for exp in profile.experience
                                if exp
                            ],
                            ensure_ascii=False,
                        )
                        if profile.experience
                        else None
                    )
                    placeholder.preferred_locations = (
                        json.dumps([loc for loc in profile.preferred_locations if loc], ensure_ascii=False)
                        if profile.preferred_locations
                        else None
                    )
                    placeholder.research_interests = (
                        json.dumps([ri for ri in profile.research_interests if ri], ensure_ascii=False)
                        if profile.research_interests
                        else None
                    )
                    placeholder.skill_embedding = json.dumps(profile.skill_embedding, ensure_ascii=False) if profile.skill_embedding else None
                    placeholder.research_embedding = json.dumps(profile.research_embedding, ensure_ascii=False) if profile.research_embedding else None
                    placeholder.status = "COMPLETED"
                    placeholder.status_message = "Parsed and refined successfully"
                    placeholder.claimed_by = None
                    placeholder.claimed_at = None
                session.commit()
                return profile_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
