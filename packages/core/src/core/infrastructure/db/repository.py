import json
from core.utils.text import strip_accents
from sqlalchemy import create_engine, update as sa_update
from sqlalchemy.orm import sessionmaker

from core.domain.interfaces.db import BaseJobRepository
from core.domain.models.job import Job
from core.domain.models.schemas import JobDetailUpdate
from core.domain.constants import JobStatus
from core.infrastructure.db.models import JobModel


class DatabaseJobRepository(BaseJobRepository):
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

    def init_db(self) -> None:
        from core.infrastructure.db.models import Base
        Base.metadata.create_all(self._engine)

    def load(self) -> list[Job]:
        session = self._SessionLocal()
        try:
            models = session.query(JobModel).all()
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def save(self, jobs: list[Job]) -> None:
        unique_jobs = {job.url: job for job in jobs}.values()
        session = self._SessionLocal()
        try:
            for job in unique_jobs:
                self._upsert_in_session(session, job)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert(self, job: Job) -> None:
        session = self._SessionLocal()
        try:
            self._upsert_in_session(session, job)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _upsert_in_session(self, session, job: Job) -> None:
        from core.infrastructure.db.models import JobOrchestrationModel
        
        existing = session.query(JobModel).filter(JobModel.url == job.url).first()
        existing_orchestrator = session.query(JobOrchestrationModel).filter(JobOrchestrationModel.job_url == job.url).first()
        
        if not existing_orchestrator:
            ref_status = JobStatus.COMPLETED if job.required_skills is not None else JobStatus.PENDING
            existing_orchestrator = JobOrchestrationModel(
                job_url=job.url,
                detection_status=JobStatus.PENDING,
                translation_status=JobStatus.PENDING,
                refinement_status=ref_status
            )
            session.add(existing_orchestrator)

        if existing:
            existing.title = strip_accents(job.title)
            existing.source = job.source
            if job.deadline is not None:
                existing.deadline = strip_accents(job.deadline)
            if job.employer is not None:
                existing.employer = strip_accents(job.employer)
            if job.location is not None:
                existing.location = strip_accents(job.location)
            if job.description is not None:
                existing.description = strip_accents(job.description)
            if job.requirements is not None:
                existing.requirements = strip_accents(job.requirements)
            if job.required_skills is not None:
                clean_skills = [strip_accents(s) for s in job.required_skills if s]
                existing.required_skills = json.dumps(clean_skills)
                existing_orchestrator.refinement_status = JobStatus.COMPLETED
            if job.education_level is not None:
                existing.education_level = strip_accents(job.education_level)
            if job.city is not None:
                existing.city = strip_accents(job.city)
            if job.country is not None:
                existing.country = strip_accents(job.country)
            if job.language_code is not None:
                existing.language_code = job.language_code
            if job.description_en is not None:
                existing.description_en = strip_accents(job.description_en)
            if job.requirements_en is not None:
                existing.requirements_en = strip_accents(job.requirements_en)
        else:
            session.add(JobModel.from_domain(job))

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

    def update_details(self, details: list[JobDetailUpdate]) -> None:
        session = self._SessionLocal()
        try:
            for d in details:
                values = {}
                if d.description is not None:
                    values["description"] = strip_accents(d.description)
                if d.requirements is not None:
                    values["requirements"] = strip_accents(d.requirements)
                if d.deadline is not None:
                    values["deadline"] = strip_accents(d.deadline)
                if d.employer is not None:
                    values["employer"] = strip_accents(d.employer)
                if d.location is not None:
                    values["location"] = strip_accents(d.location)
                if values:
                    session.execute(
                        sa_update(JobModel)
                        .where(JobModel.url == d.url)
                        .values(**values)
                    )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_refined_jobs(self) -> list[Job]:
        from core.infrastructure.db.models import JobOrchestrationModel
        session = self._SessionLocal()
        try:
            models = (
                session.query(JobModel)
                .join(JobOrchestrationModel, JobModel.url == JobOrchestrationModel.job_url)
                .filter(JobOrchestrationModel.refinement_status == JobStatus.COMPLETED)
                .all()
            )
            return [m.to_domain() for m in models]
        finally:
            session.close()

    def get_recent_urls(self, source: str, limit: int = 500) -> list[str]:
        session = self._SessionLocal()
        try:
            results = (
                session.query(JobModel.url)
                .filter(JobModel.source == source)
                .order_by(JobModel.id.desc())
                .limit(limit)
                .all()
            )
            return [r[0] for r in results]
        finally:
            session.close()
