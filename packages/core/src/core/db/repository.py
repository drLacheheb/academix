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
    or_,
    update,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from core.models.job import Job

Base = declarative_base()

STATUS_PENDING = "PENDING"
STATUS_CLAIMED = "CLAIMED"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

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

    refinement_status = Column(String, nullable=False, default=STATUS_PENDING, index=True)
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

    def claim_next_for_refinement(self, agent_name: str) -> Job | None:
        session = self._SessionLocal()
        try:
            self._recover_stale_claims(session)

            candidate = (
                session.query(JobModel)
                .filter(
                    JobModel.description.isnot(None),
                    JobModel.refinement_status == STATUS_PENDING,
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
            skills_str = json.dumps(required_skills) if required_skills is not None else None
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
        stale_cutoff = datetime.utcnow() - timedelta(minutes=STALE_CLAIM_TIMEOUT_MINUTES)
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
        if result.rowcount > 0:
            print(f"Recovered {result.rowcount} stale refinement claims.", file=sys.stderr)
        return result.rowcount



    def get_status(self) -> dict:
        session = self._SessionLocal()
        try:
            total = session.query(JobModel).count()
            pending_details = session.query(JobModel).filter(JobModel.description.is_(None)).count()
            pending_refine = session.query(JobModel).filter(JobModel.refinement_status == STATUS_PENDING, JobModel.description.isnot(None)).count()
            claimed = session.query(JobModel).filter(JobModel.refinement_status == STATUS_CLAIMED).count()
            completed = session.query(JobModel).filter(JobModel.refinement_status == STATUS_COMPLETED).count()
            failed = session.query(JobModel).filter(JobModel.refinement_status == STATUS_FAILED).count()
            return {
                "total_jobs": total,
                "pending_details": pending_details,
                "pending_refinement": pending_refine,
                "claimed_refinement": claimed,
                "completed_refinement": completed,
                "failed_refinement": failed,
            }
        finally:
            session.close()
