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


def test_api_upload_cv_valid_pdf(api_client: TestClient):
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    resp = api_client.post(
        "/profiles/upload-cv",
        files={"file": ("cv.pdf", pdf_content, "application/pdf")},
        data={"name": "Albert Einstein", "email": "albert@einstein.org"},
    )
    assert resp.status_code == 202
    assert "id" in resp.json()


def test_api_upload_cv_invalid_magic_bytes(api_client: TestClient):
    fake_pdf = b"This is just plain text, not a real PDF!"
    resp = api_client.post(
        "/profiles/upload-cv",
        files={"file": ("malicious.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 400
    assert "Invalid PDF" in resp.json()["detail"]


def test_api_upload_cv_invalid_extension(api_client: TestClient):
    script_content = b"print('hello')"
    resp = api_client.post(
        "/profiles/upload-cv",
        files={"file": ("script.py", script_content, "text/x-python")},
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_api_upload_cv_oversized_payload(api_client: TestClient, monkeypatch):
    from api.routers import profiles

    monkeypatch.setattr(profiles, "MAX_UPLOAD_SIZE_BYTES", 1024)
    oversized = b"%PDF-1.4\n" + (b"A" * 2048)
    resp = api_client.post(
        "/profiles/upload-cv",
        files={"file": ("large_cv.pdf", oversized, "application/pdf")},
    )
    assert resp.status_code == 413
    assert "maximum allowed upload size" in resp.json()["detail"]


def test_api_patch_profile_fields(api_client: TestClient, memory_repo: PipelineJobRepository):
    # 1. Create a base profile
    saved = memory_repo.profiles.save(
        CandidateProfile(
            name="Nikola Tesla",
            email="nikola@tesla.org",
            highest_degree="Master",
            skills=["Electricity", "Physics"],
            status="REFINED",
        )
    )
    profile_id = saved.id
    assert profile_id is not None

    # 2. Patch specific fields
    patch_resp = api_client.patch(
        f"/profiles/{profile_id}",
        json={
            "highest_degree": "PhD",
            "skills": ["Electromagnetism", "AC Power", "Wireless Energy"],
            "preferred_locations": ["New York", "Graz"],
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["highest_degree"] == "PhD"
    assert "AC Power" in data["skills"]
    assert "Graz" in data["preferred_locations"]


def test_api_delete_profiles(api_client: TestClient, memory_repo: PipelineJobRepository):
    # 1. Create profiles
    p1 = memory_repo.profiles.save(
        CandidateProfile(
            name="Delete Candidate 1",
            email="del1@test.com",
            telegram_chat_id="chat_del_1",
            status="REFINED",
        )
    )
    p2 = memory_repo.profiles.save(
        CandidateProfile(
            name="Delete Candidate 2",
            email="del2@test.com",
            telegram_chat_id="chat_del_2",
            status="REFINED",
        )
    )

    # 2. Delete by ID
    del_id_resp = api_client.delete(f"/profiles/{p1.id}")
    assert del_id_resp.status_code == 200
    assert del_id_resp.json()["status"] == "success"

    # 3. Delete by Telegram chat ID
    del_chat_resp = api_client.delete(f"/profiles/by-telegram-chat-id/{p2.telegram_chat_id}")
    assert del_chat_resp.status_code == 200
    assert del_chat_resp.json()["status"] == "success"

    # 4. Verify 404 on subsequent deletes
    not_found_resp = api_client.delete(f"/profiles/{p1.id}")
    assert not_found_resp.status_code == 404
