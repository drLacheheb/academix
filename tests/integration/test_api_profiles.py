from core.domain.models.profile import CandidateProfile
from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from fastapi.testclient import TestClient


def test_api_profile_lifecycle(api_client: TestClient, memory_repo: PipelineJobRepository):
    # 1. Create initial profile
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Marie Curie",
            email="marie@curie.fr",
            cv_file_path="/uploads/cv.pdf",
            status="PENDING_INGESTION",
        )
    )
    profile_id = saved.id
    assert profile_id is not None

    # 2. Submit raw text
    submit_resp = api_client.put(
        f"/profiles/submit-raw-text/{profile_id}",
        json={
            "raw_text": "Curriculum Vitae: Marie Curie. Doctorat de Physique.",
            "name": "Marie Curie",
            "email": "marie@curie.fr",
        },
    )
    assert submit_resp.status_code == 200

    # 3. Claim for translation
    claim_resp = api_client.post("/profiles/claim-translate", json={"agent_name": "worker-1"})
    assert claim_resp.status_code == 200
    claimed = claim_resp.json()["profile"]
    assert claimed is not None
    assert claimed["id"] == profile_id

    # 4. Complete translation
    trans_resp = api_client.put(
        "/profiles/translate",
        json={
            "profile_id": profile_id,
            "raw_text_en": "Curriculum Vitae: Marie Curie. PhD in Physics.",
        },
    )
    assert trans_resp.status_code == 200

    # 5. Claim for refinement
    claim_ref_resp = api_client.post("/profiles/claim-refine", json={"agent_name": "refine-1"})
    assert claim_ref_resp.status_code == 200
    assert claim_ref_resp.json()["profile"]["id"] == profile_id

    # 6. Complete refinement
    complete_ref_resp = api_client.put(
        "/profiles/refine",
        json={
            "profile_id": profile_id,
            "profile": {
                "highest_degree": "PhD",
                "skills": ["Radioactivity", "Physics", "Chemistry"],
                "research_interests": ["Nuclear Physics"],
                "degree_fields": ["Physics"],
                "languages": [{"language": "French", "proficiency": "Native"}],
            },
        },
    )
    assert complete_ref_resp.status_code == 200

    # 7. Retrieve profile list
    list_resp = api_client.get("/profiles")
    assert list_resp.status_code == 200
    profiles = list_resp.json()
    assert len(profiles) >= 1
    assert profiles[0]["email"] == "marie@curie.fr"
