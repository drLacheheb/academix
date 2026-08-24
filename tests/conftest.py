from typing import Generator

import pytest
from api.dependencies import get_repo
from api.main import app
from core.domain.models.job import Job
from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from fastapi.testclient import TestClient


@pytest.fixture
def memory_repo() -> Generator[PipelineJobRepository, None, None]:
    repo = PipelineJobRepository("sqlite:///:memory:")
    repo.init_db()
    yield repo


@pytest.fixture
def sample_job_en() -> Job:
    return Job(
        title="Postdoctoral Researcher in Quantum Physics",
        url="https://example.com/jobs/quantum-1",
        source="naturecareers",
        employer="University of Oxford",
        city="Oxford",
        country="United Kingdom",
        job_details=(
            "## Job Description\n\n"
            "We are seeking a Postdoctoral Researcher in Quantum Computing to join our group."
        ),
    )


@pytest.fixture
def sample_job_fr() -> Job:
    return Job(
        title="Postdoctorant en photonique quantique",
        url="https://example.com/jobs/quantum-fr-1",
        source="abg",
        employer="ESPCI Paris",
        city="Paris",
        country="France",
        job_details=(
            "## Description du sujet\n\n"
            "Ce projet de doctorat vise à explorer la conversion optique non linéaire "
            "dans des dispositifs quantiques."
        ),
    )


@pytest.fixture
def sample_job_hybrid() -> Job:
    return Job(
        title="Sujet de Thèse // Non-linear optical effects in polaritonic quantum devices",
        url="https://example.com/jobs/hybrid-1",
        source="abg",
        employer="ESPCI Paris",
        country="France",
        job_details=(
            "## Description du sujet\n\n"
            "Ce projet vise à explorer la conversion optique.\n\n"
            "---\n\n"
            "Nonlinear optical phenomena play a crucial role in communications.\n\n"
            "-Master 2 de Physique\n"
            "-Good knowledge of Quantum Physics"
        ),
    )


@pytest.fixture
def api_client(memory_repo: PipelineJobRepository) -> Generator[TestClient, None, None]:
    from api.dependencies import verify_token

    app.dependency_overrides[get_repo] = lambda: memory_repo
    app.dependency_overrides[verify_token] = lambda: None
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
