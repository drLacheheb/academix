from core.domain.models.job import Job
from core.domain.models.match import Match
from core.domain.models.profile import CandidateProfile
from core.domain.models.schemas import (
    EmbeddingJobResult,
    JobDetailUpdate,
    JobStubCreate,
    RefinementResult,
    TranslationResult,
)


def test_job_model_instantiation():
    job = Job(
        title="AI Engineer",
        url="https://example.com/ai-job",
        source="euraxess",
        employer="Max Planck",
        city="Munich",
        country="Germany",
        job_details="We need an AI engineer.",
    )
    data = job.to_dict()
    assert data["title"] == "AI Engineer"
    assert data["url"] == "https://example.com/ai-job"
    assert data["source"] == "euraxess"
    assert data["job_details"] == "We need an AI engineer."
    assert data["job_details_en"] is None


def test_candidate_profile_instantiation():
    profile = CandidateProfile(
        id=1,
        name="Marie Curie",
        email="marie.curie@radium.fr",
        highest_degree="PhD",
        skills=["Radiation", "Chemistry", "Physics"],
        status="PENDING_TRANSLATION",
    )
    data = profile.to_dict()
    assert data["id"] == 1
    assert data["name"] == "Marie Curie"
    assert data["highest_degree"] == "PhD"
    assert "Physics" in data["skills"]


def test_match_instantiation():
    match = Match(
        candidate_id=10,
        job_url="https://example.com/job",
        score=0.88,
        degree_eligible=True,
        language_eligible=True,
        skill_score=0.9,
        research_score=0.85,
    )
    assert match.candidate_id == 10
    assert match.score == 0.88
    assert match.degree_eligible is True


def test_pydantic_schemas_validation():
    stub = JobStubCreate(title="PhD in Robotics", url="https://example.com/phd", source="abg")
    assert stub.title == "PhD in Robotics"

    details = JobDetailUpdate(
        url="https://example.com/phd",
        job_details="Detailed PhD description",
    )
    assert details.job_details == "Detailed PhD description"

    trans = TranslationResult(url="https://example.com/phd", job_details_en="English text")
    assert trans.job_details_en == "English text"

    ref = RefinementResult(
        url="https://example.com/phd",
        required_skills=["ROS", "C++"],
        education_level="Master",
        degree_fields=["Robotics", "Computer Science"],
    )
    assert "ROS" in ref.required_skills
    assert ref.education_level == "Master"

    emb = EmbeddingJobResult(
        url="https://example.com/phd",
        skill_embedding=[0.1, 0.2],
        research_embedding=[0.3, 0.4],
    )
    assert emb.skill_embedding is not None
    assert len(emb.skill_embedding) == 2
