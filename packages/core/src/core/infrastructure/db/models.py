import json
from core.utils.text import strip_accents
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import declarative_base

from core.domain.models.job import Job
from core.domain.constants import JobStatus

Base = declarative_base()


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
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    detection_claimed_by = Column(String, nullable=True)
    detection_claimed_at = Column(DateTime, nullable=True)

    translation_status = Column(
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    translation_claimed_by = Column(String, nullable=True)
    translation_claimed_at = Column(DateTime, nullable=True)

    refinement_status = Column(
        String, nullable=False, default=JobStatus.PENDING, index=True
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
            json.dumps([strip_accents(s) for s in job.required_skills if s])
            if job.required_skills is not None
            else None
        )

        if job.required_skills is not None:
            status = JobStatus.COMPLETED
        else:
            status = JobStatus.PENDING

        return cls(
            title=strip_accents(job.title),
            url=job.url,
            source=job.source,
            deadline=strip_accents(job.deadline),
            employer=strip_accents(job.employer),
            location=strip_accents(job.location),
            description=strip_accents(job.description),
            requirements=strip_accents(job.requirements),
            required_skills=skills_str,
            education_level=strip_accents(job.education_level),
            city=strip_accents(job.city),
            country=strip_accents(job.country),
            refinement_status=status,
            language_code=job.language_code,
            description_en=strip_accents(job.description_en),
            requirements_en=strip_accents(job.requirements_en),
        )
