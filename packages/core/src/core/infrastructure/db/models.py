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
from core.domain.models.profile import CandidateProfile
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


class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    cv_file_path = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    highest_degree = Column(String, nullable=True)
    skills = Column(Text, nullable=True)  # JSON array of strings
    languages = Column(Text, nullable=True)  # JSON array of dicts: [{"language": "...", "proficiency": "..."}]
    experience = Column(Text, nullable=True)  # JSON array of dicts: [{"role": "...", "organization": "...", "from_date": "...", "to_date": "...", "description": "..."}]
    preferred_locations = Column(Text, nullable=True)  # JSON array of strings
    research_interests = Column(Text, nullable=True)  # JSON array of strings
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def to_domain(self) -> CandidateProfile:
        return CandidateProfile(
            id=self.id,
            name=self.name,
            email=self.email,
            cv_file_path=self.cv_file_path,
            raw_text=self.raw_text,
            highest_degree=self.highest_degree,
            skills=json.loads(self.skills) if self.skills else [],
            languages=json.loads(self.languages) if self.languages else [],
            experience=json.loads(self.experience) if self.experience else [],
            preferred_locations=json.loads(self.preferred_locations) if self.preferred_locations else [],
            research_interests=json.loads(self.research_interests) if self.research_interests else [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, profile: CandidateProfile) -> "CandidateProfileModel":
        return cls(
            id=profile.id,
            name=strip_accents(profile.name),
            email=profile.email,
            cv_file_path=profile.cv_file_path,
            raw_text=profile.raw_text,
            highest_degree=strip_accents(profile.highest_degree),
            skills=json.dumps([strip_accents(s) for s in profile.skills if s]) if profile.skills is not None else None,
            languages=json.dumps([{"language": strip_accents(l.get("language")), "proficiency": strip_accents(l.get("proficiency"))} for l in profile.languages if l]) if profile.languages is not None else None,
            experience=json.dumps([{
                "role": strip_accents(exp.get("role")),
                "organization": strip_accents(exp.get("organization")),
                "from_date": strip_accents(exp.get("from_date")),
                "to_date": strip_accents(exp.get("to_date")),
                "description": strip_accents(exp.get("description"))
            } for exp in profile.experience if exp]) if profile.experience is not None else None,
            preferred_locations=json.dumps([strip_accents(loc) for loc in profile.preferred_locations if loc]) if profile.preferred_locations is not None else None,
            research_interests=json.dumps([strip_accents(ri) for ri in profile.research_interests if ri]) if profile.research_interests is not None else None,
        )

