from fastapi.testclient import TestClient


def test_api_claim_and_complete_translation(api_client: TestClient):
    # Insert job stub and update details
    api_client.post(
        "/jobs",
        json=[{"title": "Sujet de thèse", "url": "https://example.com/fr-job", "source": "abg"}],
    )
    api_client.put(
        "/jobs/details",
        json=[
            {
                "url": "https://example.com/fr-job",
                "job_details": (
                    "## Description du sujet\n\nCe projet vise à explorer la conversion optique."
                ),
            }
        ],
    )

    # 1. Claim translation job
    claim_resp = api_client.post("/jobs/claim-translate", json={"agent_name": "worker-trans-1"})
    assert claim_resp.status_code == 200
    claimed = claim_resp.json()["job"]
    assert claimed is not None
    assert claimed["url"] == "https://example.com/fr-job"

    # 2. Submit translated text
    trans_resp = api_client.put(
        "/jobs/translate",
        json={
            "url": "https://example.com/fr-job",
            "job_details_en": (
                "## Description of the subject\n\nThis project aims to explore optical conversion."
            ),
        },
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "completed"


def test_api_translation_skip_english(api_client: TestClient):
    api_client.post(
        "/jobs",
        json=[
            {
                "title": "Postdoc in Physics",
                "url": "https://example.com/en-job",
                "source": "naturecareers",
            }
        ],
    )
    api_client.put(
        "/jobs/details",
        json=[
            {
                "url": "https://example.com/en-job",
                "job_details": "## Job Description\n\nPure English job posting.",
            }
        ],
    )

    # Claim
    claim_resp = api_client.post("/jobs/claim-translate", json={"agent_name": "worker-trans-1"})
    assert claim_resp.status_code == 200
    assert claim_resp.json()["job"]["url"] == "https://example.com/en-job"

    # Submit with job_details_en: None (skipped)
    skip_resp = api_client.put(
        "/jobs/translate",
        json={"url": "https://example.com/en-job", "job_details_en": None},
    )
    assert skip_resp.status_code == 200
