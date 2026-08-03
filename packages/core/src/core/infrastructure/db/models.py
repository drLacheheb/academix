import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

from core.domain.constants import JobStatus
from core.domain.models.job import Job
from core.domain.models.match import Match
from core.domain.models.profile import CandidateProfile

Base = declarative_base()


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    deadline: Mapped[str | None] = mapped_column(String, nullable=True)
    employer: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_interests: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)

    language_code: Mapped[str | None] = mapped_column(String, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_domain(self) -> Job:
        required_skills_list: list[str] | None = None
        if self.required_skills:
            try:
                required_skills_list = json.loads(self.required_skills)
            except Exception:
                required_skills_list = None

        research_interests_list: list[str] | None = None
        if self.research_interests:
            try:
                research_interests_list = json.loads(self.research_interests)
            except Exception:
                research_interests_list = None

        skill_emb: list[float] | None = None
        if self.skill_embedding:
            try:
                skill_emb = json.loads(self.skill_embedding)
            except Exception:
                skill_emb = None

        research_emb: list[float] | None = None
        if self.research_embedding:
            try:
                research_emb = json.loads(self.research_embedding)
            except Exception:
                research_emb = None

        return Job(
            url=self.url,
            title=self.title,
            source=self.source,
            deadline=self.deadline,
            employer=self.employer,
            location=self.location,
            description=self.description,
            requirements=self.requirements,
            required_skills=required_skills_list,
            research_interests=research_interests_list,
            education_level=self.education_level,
            city=self.city,
            country=self.country,
            language_code=self.language_code,
            description_en=self.description_en,
            requirements_en=self.requirements_en,
            skill_embedding=skill_emb,
            research_embedding=research_emb,
        )

    @classmethod
    def from_domain(cls, job: Job) -> "JobModel":
        skills_str = (
            json.dumps([s for s in job.required_skills if s], ensure_ascii=False)
            if job.required_skills is not None
            else None
        )
        research_str = (
            json.dumps([s for s in job.research_interests if s], ensure_ascii=False)
            if job.research_interests is not None
            else None
        )

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
            research_interests=research_str,
            education_level=job.education_level,
            city=job.city,
            country=job.country,
            language_code=job.language_code,
            description_en=job.description_en,
            requirements_en=job.requirements_en,
            skill_embedding=json.dumps(job.skill_embedding, ensure_ascii=False)
            if job.skill_embedding is not None
            else None,
            research_embedding=json.dumps(job.research_embedding, ensure_ascii=False)
            if job.research_embedding is not None
            else None,
        )


class JobOrchestrationModel(Base):
    __tablename__ = "job_orchestrations"

    job_url: Mapped[str] = mapped_column(
        String,
        ForeignKey("jobs.url", ondelete="CASCADE"),
        primary_key=True,
    )

    detection_status: Mapped[str] = mapped_column(
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    detection_claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    detection_claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    translation_status: Mapped[str] = mapped_column(
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    translation_claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    translation_claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    refinement_status: Mapped[str] = mapped_column(
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    embedding_status: Mapped[str] = mapped_column(
        String, nullable=False, default=JobStatus.PENDING, index=True
    )
    embedding_claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def _safe_json_loads(val: str | None, default: Any = None) -> Any:
    if not val:
        return default
    try:
        return json.loads(val)
    except Exception:
        return default


class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    cv_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    highest_degree: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_locations: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_interests: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="INGESTING", index=True)
    status_message: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    is_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_domain(self) -> CandidateProfile:
        return CandidateProfile(
            id=self.id,
            name=self.name,
            email=self.email,
            cv_file_path=self.cv_file_path,
            raw_text=self.raw_text,
            language_code=self.language_code,
            raw_text_en=self.raw_text_en,
            highest_degree=self.highest_degree,
            skills=_safe_json_loads(self.skills, []),
            languages=_safe_json_loads(self.languages, []),
            preferred_locations=_safe_json_loads(self.preferred_locations, []),
            research_interests=_safe_json_loads(self.research_interests, []),
            skill_embedding=_safe_json_loads(self.skill_embedding, None),
            research_embedding=_safe_json_loads(self.research_embedding, None),
            status=self.status,
            status_message=self.status_message,
            claimed_by=self.claimed_by,
            claimed_at=self.claimed_at,
            telegram_chat_id=self.telegram_chat_id,
            is_notified=self.is_notified,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, profile: CandidateProfile) -> "CandidateProfileModel":
        return cls(
            id=profile.id,
            name=profile.name if profile.name else None,
            email=profile.email,
            cv_file_path=profile.cv_file_path,
            raw_text=profile.raw_text,
            language_code=profile.language_code,
            raw_text_en=profile.raw_text_en,
            highest_degree=profile.highest_degree if profile.highest_degree else None,
            skills=json.dumps([s for s in profile.skills if s], ensure_ascii=False)
            if profile.skills is not None
            else None,
            languages=json.dumps(
                [
                    {
                        "language": lang.get("language") if isinstance(lang, dict) else str(lang),
                        "proficiency": lang.get("proficiency") if isinstance(lang, dict) else None,
                    }
                    for lang in profile.languages
                    if lang
                ],
                ensure_ascii=False,
            )
            if profile.languages is not None
            else None,
            preferred_locations=json.dumps(
                [loc for loc in profile.preferred_locations if loc],
                ensure_ascii=False,
            )
            if profile.preferred_locations is not None
            else None,
            research_interests=json.dumps(
                [ri for ri in profile.research_interests if ri],
                ensure_ascii=False,
            )
            if profile.research_interests is not None
            else None,
            skill_embedding=json.dumps(profile.skill_embedding, ensure_ascii=False)
            if profile.skill_embedding is not None
            else None,
            research_embedding=json.dumps(profile.research_embedding, ensure_ascii=False)
            if profile.research_embedding is not None
            else None,
            status=profile.status,
            status_message=profile.status_message,
            claimed_by=profile.claimed_by,
            claimed_at=profile.claimed_at,
            telegram_chat_id=profile.telegram_chat_id,
            is_notified=profile.is_notified,
        )


class MatchingQueueModel(Base):
    __tablename__ = "matching_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class MatchModel(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_url: Mapped[str] = mapped_column(
        String,
        ForeignKey("jobs.url", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    degree_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    language_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    research_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending", index=True
    )
    explanation_claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    explanation_claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telegram_notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    telegram_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("candidate_id", "job_url", name="uq_candidate_job_match"),)

    def to_domain(self) -> Match:
        return Match(
            id=self.id,
            candidate_id=self.candidate_id,
            job_url=self.job_url,
            score=self.score,
            degree_eligible=self.degree_eligible,
            language_eligible=self.language_eligible,
            skill_score=self.skill_score,
            research_score=self.research_score,
            explanation=self.explanation,
            explanation_status=self.explanation_status,
            telegram_notified=self.telegram_notified,
            telegram_notified_at=self.telegram_notified_at,
            created_at=self.created_at,
        )


class CrawlerCheckpointModel(Base):
    __tablename__ = "crawler_checkpoints"

    source: Mapped[str] = mapped_column(String, primary_key=True)
    last_successful_url: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
