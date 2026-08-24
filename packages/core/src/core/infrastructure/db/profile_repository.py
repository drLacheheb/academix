import json
from datetime import datetime

from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

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
                    connect_args={"timeout": 60, "check_same_thread": False},
                )
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
                    existing.preferred_locations = model.preferred_locations
                    existing.research_interests = model.research_interests
                    existing.status = model.status
                    existing.status_message = model.status_message
                    existing.claimed_by = model.claimed_by
                    existing.claimed_at = model.claimed_at
                    existing.is_notified = model.is_notified
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

    def get_by_telegram_chat_id(self, chat_id: str) -> list[CandidateProfile]:
        if not chat_id:
            return []
        session = self._SessionLocal()
        try:
            models = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.telegram_chat_id == str(chat_id))
                .order_by(CandidateProfileModel.created_at.desc())
                .all()
            )
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def get_unnotified_completed(self, limit: int = 10) -> list[CandidateProfile]:
        session = self._SessionLocal()
        try:
            valid_statuses = ["PENDING_EMBEDDING", "EMBEDDING_CLAIMED", "COMPLETED"]
            models = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.telegram_chat_id.isnot(None),
                    CandidateProfileModel.is_notified == False,  # noqa: E712
                    CandidateProfileModel.status.in_(valid_statuses),
                )
                .order_by(CandidateProfileModel.updated_at.asc())
                .limit(limit)
                .all()
            )
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def mark_notified(self, profile_ids: list[int]) -> int:
        if not profile_ids:
            return 0
        session = self._SessionLocal()
        try:
            count = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id.in_(profile_ids))
                .update({"is_notified": True}, synchronize_session=False)
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_profile_fields(self, profile_id: int, fields: dict) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if not existing:
                return None

            clear_embeddings = False
            if "name" in fields:
                existing.name = fields["name"]
            if "highest_degree" in fields:
                existing.highest_degree = fields["highest_degree"]
            if "skills" in fields:
                skills_val = fields["skills"]
                existing.skills = (
                    json.dumps(skills_val, ensure_ascii=False)
                    if isinstance(skills_val, list)
                    else skills_val
                )
                clear_embeddings = True
            if "research_interests" in fields:
                ri_val = fields["research_interests"]
                existing.research_interests = (
                    json.dumps(ri_val, ensure_ascii=False) if isinstance(ri_val, list) else ri_val
                )
                clear_embeddings = True
            if "preferred_locations" in fields:
                loc_val = fields["preferred_locations"]
                existing.preferred_locations = (
                    json.dumps(loc_val, ensure_ascii=False)
                    if isinstance(loc_val, list)
                    else loc_val
                )
            if "languages" in fields:
                lang_val = fields["languages"]
                existing.languages = (
                    json.dumps(lang_val, ensure_ascii=False)
                    if isinstance(lang_val, list)
                    else lang_val
                )

            if clear_embeddings:
                existing.skill_embedding = None
                existing.research_embedding = None

            # Purge existing matches and matching queue entries for this candidate
            from core.infrastructure.db.models import MatchingQueueModel, MatchModel

            session.query(MatchModel).filter(MatchModel.candidate_id == profile_id).delete()
            session.query(MatchingQueueModel).filter(
                MatchingQueueModel.entity_type == "candidate",
                MatchingQueueModel.entity_id == str(profile_id),
            ).delete()

            existing.status = "PENDING_REFINEMENT"
            existing.status_message = (
                "Updated manually via Telegram. Pending embedding re-generation."
            )

            session.commit()
            session.refresh(existing)
            return existing.to_domain()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_by_telegram_chat_id(self, telegram_chat_id: str) -> bool:
        session = self._SessionLocal()
        try:
            from core.infrastructure.db.models import MatchingQueueModel, MatchModel

            profiles = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.telegram_chat_id == telegram_chat_id)
                .all()
            )
            if not profiles:
                return False

            for profile in profiles:
                # Delete matches and matching queue entries
                session.query(MatchModel).filter(MatchModel.candidate_id == profile.id).delete()
                session.query(MatchingQueueModel).filter(
                    MatchingQueueModel.entity_type == "candidate",
                    MatchingQueueModel.entity_id == str(profile.id),
                ).delete()

                # Delete CV file via StorageService abstraction (supports Local & S3)
                if profile.cv_file_path:
                    try:
                        from core.infrastructure.services.storage import (
                            get_storage_service_from_env,
                        )

                        get_storage_service_from_env().delete(profile.cv_file_path)
                    except Exception:
                        pass

                session.delete(profile)

            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_by_id(self, profile_id: int) -> bool:
        session = self._SessionLocal()
        try:
            from core.infrastructure.db.models import MatchingQueueModel, MatchModel

            profile = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if not profile:
                return False

            # Delete matches and matching queue entries
            session.query(MatchModel).filter(MatchModel.candidate_id == profile_id).delete()
            session.query(MatchingQueueModel).filter(
                MatchingQueueModel.entity_type == "candidate",
                MatchingQueueModel.entity_id == str(profile_id),
            ).delete()

            # Delete CV file via StorageService abstraction (supports Local & S3)
            if profile.cv_file_path:
                try:
                    from core.infrastructure.services.storage import (
                        get_storage_service_from_env,
                    )

                    get_storage_service_from_env().delete(profile.cv_file_path)
                except Exception:
                    pass

            session.delete(profile)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
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

            if getattr(result, "rowcount", 0) > 0:
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
                existing.skills = (
                    json.dumps(profile.skills, ensure_ascii=False) if profile.skills else None
                )
                existing.languages = (
                    json.dumps(profile.languages, ensure_ascii=False) if profile.languages else None
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
                existing.status = "PENDING_TRANSLATION"
                existing.status_message = "Raw text parsed successfully"
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
            if getattr(result, "rowcount", 0) > 0:
                session.refresh(candidate)
                return candidate.to_domain()
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_translation(self, profile_id: int, raw_text_en: str | None = None) -> None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                if raw_text_en is not None:
                    existing.raw_text_en = raw_text_en
                existing.status = "PENDING_REFINEMENT"
                existing.status_message = (
                    "Translation completed" if raw_text_en else "Translation skipped (English)"
                )
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
            if getattr(result, "rowcount", 0) > 0:
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
                    existing_email.cv_file_path = (
                        placeholder.cv_file_path or existing_email.cv_file_path
                    )
                    existing_email.raw_text = placeholder.raw_text or existing_email.raw_text
                    existing_email.raw_text_en = (
                        placeholder.raw_text_en or existing_email.raw_text_en
                    )
                    existing_email.telegram_chat_id = (
                        placeholder.telegram_chat_id or existing_email.telegram_chat_id
                    )
                existing_email.highest_degree = (
                    profile.highest_degree if profile.highest_degree else None
                )
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

                existing_email.preferred_locations = (
                    json.dumps(
                        [loc for loc in profile.preferred_locations if loc],
                        ensure_ascii=False,
                    )
                    if profile.preferred_locations
                    else None
                )
                existing_email.research_interests = (
                    json.dumps(
                        [ri for ri in profile.research_interests if ri],
                        ensure_ascii=False,
                    )
                    if profile.research_interests
                    else None
                )
                existing_email.skill_embedding = None
                existing_email.research_embedding = None
                existing_email.status = "PENDING_EMBEDDING"
                existing_email.status_message = "Refinement completed, awaiting embedding"
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
                    placeholder.highest_degree = (
                        profile.highest_degree if profile.highest_degree else None
                    )
                    placeholder.degree_fields = (
                        json.dumps([df for df in profile.degree_fields if df], ensure_ascii=False)
                        if profile.degree_fields
                        else None
                    )
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

                    placeholder.preferred_locations = (
                        json.dumps(
                            [loc for loc in profile.preferred_locations if loc],
                            ensure_ascii=False,
                        )
                        if profile.preferred_locations
                        else None
                    )
                    placeholder.research_interests = (
                        json.dumps(
                            [ri for ri in profile.research_interests if ri],
                            ensure_ascii=False,
                        )
                        if profile.research_interests
                        else None
                    )
                    placeholder.skill_embedding = None
                    placeholder.research_embedding = None
                    placeholder.status = "PENDING_EMBEDDING"
                    placeholder.status_message = "Refinement completed, awaiting embedding"
                    placeholder.claimed_by = None
                    placeholder.claimed_at = None
                session.commit()
                return profile_id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_embedding(
        self, agent_name: str, stale_cutoff: datetime
    ) -> CandidateProfile | None:
        session = self._SessionLocal()
        try:
            # Recover stale embedding claims
            session.execute(
                update(CandidateProfileModel)
                .where(
                    CandidateProfileModel.status == "EMBEDDING_CLAIMED",
                    CandidateProfileModel.claimed_at < stale_cutoff,
                )
                .values(
                    status="PENDING_EMBEDDING",
                    claimed_by=None,
                    claimed_at=None,
                )
            )
            candidate = (
                session.query(CandidateProfileModel)
                .filter(
                    CandidateProfileModel.status == "PENDING_EMBEDDING",
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
                    CandidateProfileModel.status == "PENDING_EMBEDDING",
                    CandidateProfileModel.claimed_by.is_(None),
                )
                .values(
                    status="EMBEDDING_CLAIMED",
                    claimed_by=agent_name,
                    claimed_at=datetime.now(),
                )
            )
            session.commit()
            if getattr(result, "rowcount", 0) > 0:
                session.refresh(candidate)
                return candidate.to_domain()
            return None
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete_embedding(
        self,
        profile_id: int,
        skill_embedding: list[float] | None,
        research_embedding: list[float] | None,
        degree_embedding: list[float] | None,
    ) -> None:
        session = self._SessionLocal()
        try:
            existing = (
                session.query(CandidateProfileModel)
                .filter(CandidateProfileModel.id == profile_id)
                .first()
            )
            if existing:
                existing.skill_embedding = (
                    json.dumps(skill_embedding, ensure_ascii=False)
                    if skill_embedding is not None
                    else None
                )
                existing.research_embedding = (
                    json.dumps(research_embedding, ensure_ascii=False)
                    if research_embedding is not None
                    else None
                )
                existing.degree_embedding = (
                    json.dumps(degree_embedding, ensure_ascii=False)
                    if degree_embedding is not None
                    else None
                )
                existing.status = "COMPLETED"
                existing.status_message = "Embedding completed successfully"
                existing.claimed_by = None
                existing.claimed_at = None
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
