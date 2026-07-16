import json
import sys
from datetime import datetime, timedelta

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    update,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from core.models.job import Job

Base = declarative_base()

STATUS_PENDING = "PENDING"
STATUS_CLAIMED = "CLAIMED"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"

STALE_CLAIM_TIMEOUT_MINUTES = 10


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    deadline = Column(String, nullable=True)
    employer = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    education_level = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)

    language_code = Column(String, nullable=True)
    description_en = Column(Text, nullable=True)
    requirements_en = Column(Text, nullable=True)

    detection_status = Column(
        String, nullable=False, default=STATUS_PENDING, index=True
    )
    detection_claimed_by = Column(String, nullable=True)
    detection_claimed_at = Column(DateTime, nullable=True)

    translation_status = Column(
        String, nullable=False, default=STATUS_PENDING, index=True
    )
    translation_claimed_by = Column(String, nullable=True)
    translation_claimed_at = Column(DateTime, nullable=True)

    refinement_status = Column(
        String, nullable=False, default=STATUS_PENDING, index=True
    )
    claimed_by = Column(String, nullable=True)
    claimed_at = Column(DateTime, nullable=True)

    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_domain(self) -> Job:
        try:
            skills_list = (
                json.loads(self.required_skills) if self.required_skills else None
            )
        except Exception:
            skills_list = None

        return Job(
            title=self.title,
            url=self.url,
            source=self.source,
            deadline=self.deadline,
            employer=self.employer,
            location=self.location,
            description=self.description,
            requirements=self.requirements,
            required_skills=skills_list,
            education_level=self.education_level,
            city=self.city,
            country=self.country,
            language_code=self.language_code,
            description_en=self.description_en,
            requirements_en=self.requirements_en,
        )

    @classmethod
    def from_domain(cls, job: Job) -> "JobModel":
        skills_str = (
            json.dumps(job.required_skills) if job.required_skills is not None else None
        )

        if job.required_skills is not None:
            status = STATUS_COMPLETED
        else:
            status = STATUS_PENDING

        return cls(
            title=job.title,
            url=job.url,
            source=job.source,
            deadline=job.deadline,
            employer=job.employer,
            location=job.location,
            description=job.description,
            requirements=job.requirements,
            required_skills=skills_str,
            education_level=job.education_level,
            city=job.city,
            country=job.country,
            refinement_status=status,
            language_code=job.language_code,
            description_en=job.description_en,
            requirements_en=job.requirements_en,
        )


class DatabaseJobRepository:
    def __init__(self, database_url: str):
        self._database_url = database_url
        if database_url.startswith("sqlite"):
            self._engine = create_engine(
                database_url, echo=False, connect_args={"timeout": 30}
            )
        else:
            self._engine = create_engine(database_url, echo=False)
        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )
        self.init_db()

    def init_db(self) -> None:
        Base.metadata.create_all(self._engine)

    def load(self) -> list[Job]:
        session = self._SessionLocal()
        try:
            models = session.query(JobModel).all()
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def save(self, jobs: list[Job]) -> None:
        session = self._SessionLocal()
        try:
            seen_in_batch = {}
            for job in jobs:
                if job.url in seen_in_batch:
                    continue
                seen_in_batch[job.url] = job

            for job in seen_in_batch.values():
                self._upsert_in_session(session, job)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving batch to database: {e}", file=sys.stderr)
            raise e
        finally:
            session.close()

    def upsert(self, job: Job) -> None:
        session = self._SessionLocal()
        try:
            self._upsert_in_session(session, job)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error upserting job to database: {e}", file=sys.stderr)
            raise e
        finally:
            session.close()

    def _upsert_in_session(self, session, job: Job) -> None:
        existing = session.query(JobModel).filter(JobModel.url == job.url).first()
        skills_str = (
            json.dumps(job.required_skills) if job.required_skills is not None else None
        )

        if existing:
            existing.title = job.title
            existing.source = job.source
            existing.deadline = job.deadline
            existing.employer = job.employer
            existing.location = job.location
            existing.description = job.description
            existing.requirements = job.requirements
            existing.required_skills = skills_str
            existing.education_level = job.education_level
            existing.city = job.city
            existing.country = job.country
            existing.language_code = job.language_code
            existing.description_en = job.description_en
            existing.requirements_en = job.requirements_en
            if job.required_skills is not None:
                existing.refinement_status = STATUS_COMPLETED
        else:
            new_model = JobModel.from_domain(job)
            session.add(new_model)

    def get_all_urls(self) -> set[str]:
        session = self._SessionLocal()
        try:
            results = session.query(JobModel.url).all()
            return {r[0] for r in results}
        finally:
            session.close()

    def get_known_urls(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        session = self._SessionLocal()
        try:
            batch_size = 500
            known_set = set()
            for i in range(0, len(urls), batch_size):
                sub_list = urls[i : i + batch_size]
                results = (
                    session.query(JobModel.url).filter(JobModel.url.in_(sub_list)).all()
                )
                known_set.update(r[0] for r in results)
            return known_set
        finally:
            session.close()

    def get_unstored(self, source: str | None = None) -> list[Job]:
        session = self._SessionLocal()
        try:
            query = session.query(JobModel).filter(JobModel.description.is_(None))
            if source:
                query = query.filter(JobModel.source == source)
            models = query.all()
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def claim_next_for_detection(self, agent_name: str) -> Job | None:
        session = self._SessionLocal()
        try:
            self._recover_stale_claims(session)

            candidate = (
                session.query(JobModel)
                .filter(
                    JobModel.description.isnot(None),
                    JobModel.detection_status == STATUS_PENDING,
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(JobModel)
                .where(
                    JobModel.id == candidate.id,
                    JobModel.detection_status == STATUS_PENDING,
                )
                .values(
                    detection_status=STATUS_CLAIMED,
                    detection_claimed_by=agent_name,
                    detection_claimed_at=datetime.utcnow(),
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

    def complete_detection(self, url: str, language_code: str) -> None:
        session = self._SessionLocal()
        try:
            translation_status = (
                STATUS_SKIPPED if language_code == "en" else STATUS_PENDING
            )
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    language_code=language_code,
                    detection_status=STATUS_COMPLETED,
                    detection_claimed_by=None,
                    detection_claimed_at=None,
                    translation_status=translation_status,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_detection(self, url: str) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    detection_status=STATUS_FAILED,
                    detection_claimed_by=None,
                    detection_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_translation(self, agent_name: str) -> Job | None:
        session = self._SessionLocal()
        try:
            self._recover_stale_claims(session)

            candidate = (
                session.query(JobModel)
                .filter(
                    JobModel.translation_status == STATUS_PENDING,
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(JobModel)
                .where(
                    JobModel.id == candidate.id,
                    JobModel.translation_status == STATUS_PENDING,
                )
                .values(
                    translation_status=STATUS_CLAIMED,
                    translation_claimed_by=agent_name,
                    translation_claimed_at=datetime.utcnow(),
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

    def complete_translation(
        self,
        url: str,
        description_en: str | None,
        requirements_en: str | None,
    ) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    description_en=description_en,
                    requirements_en=requirements_en,
                    translation_status=STATUS_COMPLETED,
                    translation_claimed_by=None,
                    translation_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_translation(self, url: str) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    translation_status=STATUS_FAILED,
                    translation_claimed_by=None,
                    translation_claimed_at=None,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_for_refinement(self, agent_name: str) -> Job | None:
        session = self._SessionLocal()
        try:
            self._recover_stale_claims(session)

            candidate = (
                session.query(JobModel)
                .filter(
                    JobModel.description.isnot(None),
                    JobModel.refinement_status == STATUS_PENDING,
                    JobModel.translation_status.in_([STATUS_COMPLETED, STATUS_SKIPPED]),
                )
                .first()
            )
            if not candidate:
                session.commit()
                return None

            result = session.execute(
                update(JobModel)
                .where(
                    JobModel.id == candidate.id,
                    JobModel.refinement_status == STATUS_PENDING,
                )
                .values(
                    refinement_status=STATUS_CLAIMED,
                    claimed_by=agent_name,
                    claimed_at=datetime.utcnow(),
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

    def complete_refinement(
        self,
        url: str,
        required_skills: list[str],
        education_level: str | None,
        city: str | None = None,
        country: str | None = None,
    ) -> None:
        session = self._SessionLocal()
        try:
            skills_str = (
                json.dumps(required_skills) if required_skills is not None else None
            )
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    required_skills=skills_str,
                    education_level=education_level,
                    city=city,
                    country=country,
                    refinement_status=STATUS_COMPLETED,
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

    def fail_refinement(self, url: str) -> None:
        session = self._SessionLocal()
        try:
            session.execute(
                update(JobModel)
                .where(JobModel.url == url)
                .values(
                    refinement_status=STATUS_FAILED,
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

    def _recover_stale_claims(self, session) -> int:
        stale_cutoff = datetime.utcnow() - timedelta(
            minutes=STALE_CLAIM_TIMEOUT_MINUTES
        )
        recovered = 0

        # Refinement stale recovery
        result = session.execute(
            update(JobModel)
            .where(
                JobModel.refinement_status == STATUS_CLAIMED,
                JobModel.claimed_at < stale_cutoff,
            )
            .values(
                refinement_status=STATUS_PENDING,
                claimed_at=None,
                claimed_by=None,
            )
        )
        recovered += result.rowcount

        # Detection stale recovery
        result_det = session.execute(
            update(JobModel)
            .where(
                JobModel.detection_status == STATUS_CLAIMED,
                JobModel.detection_claimed_at < stale_cutoff,
            )
            .values(
                detection_status=STATUS_PENDING,
                detection_claimed_at=None,
                detection_claimed_by=None,
            )
        )
        recovered += result_det.rowcount

        # Translation stale recovery
        result_trans = session.execute(
            update(JobModel)
            .where(
                JobModel.translation_status == STATUS_CLAIMED,
                JobModel.translation_claimed_at < stale_cutoff,
            )
            .values(
                translation_status=STATUS_PENDING,
                translation_claimed_at=None,
                translation_claimed_by=None,
            )
        )
        recovered += result_trans.rowcount

        if recovered > 0:
            print(
                f"Recovered {recovered} stale claims across all stages.",
                file=sys.stderr,
            )
        return recovered

    def get_status(self) -> dict:
        session = self._SessionLocal()
        try:
            total = session.query(JobModel).count()
            pending_details = (
                session.query(JobModel).filter(JobModel.description.is_(None)).count()
            )

            # Detection stats
            pending_detect = (
                session.query(JobModel)
                .filter(
                    JobModel.description.isnot(None),
                    JobModel.detection_status == STATUS_PENDING,
                )
                .count()
            )
            claimed_detect = (
                session.query(JobModel)
                .filter(JobModel.detection_status == STATUS_CLAIMED)
                .count()
            )
            completed_detect = (
                session.query(JobModel)
                .filter(JobModel.detection_status == STATUS_COMPLETED)
                .count()
            )
            failed_detect = (
                session.query(JobModel)
                .filter(JobModel.detection_status == STATUS_FAILED)
                .count()
            )

            # Translation stats
            pending_translate = (
                session.query(JobModel)
                .filter(JobModel.translation_status == STATUS_PENDING)
                .count()
            )
            claimed_translate = (
                session.query(JobModel)
                .filter(JobModel.translation_status == STATUS_CLAIMED)
                .count()
            )
            completed_translate = (
                session.query(JobModel)
                .filter(JobModel.translation_status == STATUS_COMPLETED)
                .count()
            )
            skipped_translate = (
                session.query(JobModel)
                .filter(JobModel.translation_status == STATUS_SKIPPED)
                .count()
            )
            failed_translate = (
                session.query(JobModel)
                .filter(JobModel.translation_status == STATUS_FAILED)
                .count()
            )

            # Refinement stats
            pending_refine = (
                session.query(JobModel)
                .filter(
                    JobModel.refinement_status == STATUS_PENDING,
                    JobModel.translation_status.in_([STATUS_COMPLETED, STATUS_SKIPPED]),
                )
                .count()
            )
            claimed_refine = (
                session.query(JobModel)
                .filter(JobModel.refinement_status == STATUS_CLAIMED)
                .count()
            )
            completed_refine = (
                session.query(JobModel)
                .filter(JobModel.refinement_status == STATUS_COMPLETED)
                .count()
            )
            failed_refine = (
                session.query(JobModel)
                .filter(JobModel.refinement_status == STATUS_FAILED)
                .count()
            )

            return {
                "total_jobs": total,
                "pending_details": pending_details,
                "pending_detection": pending_detect,
                "claimed_detection": claimed_detect,
                "completed_detection": completed_detect,
                "failed_detection": failed_detect,
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
