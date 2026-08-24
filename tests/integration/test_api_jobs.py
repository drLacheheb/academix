from fastapi.testclient import TestClient


def test_api_status_endpoint(api_client: TestClient):
    resp = api_client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "pending_translation" in data
    assert "pending_refinement" in data


def test_api_create_and_query_jobs(api_client: TestClient):
    # 1. Create discovery job stubs
    stubs = [
        {
            "title": "PhD Position in AI",
            "url": "https://example.com/job-api-1",
            "source": "euraxess",
        },
        {"title": "Postdoc in Quantum", "url": "https://example.com/job-api-2", "source": "abg"},
    ]
    create_resp = api_client.post("/jobs", json=stubs)
    assert create_resp.status_code == 200
    assert create_resp.json()["inserted"] == 2

    # 2. Check known URLs
    known_resp = api_client.post(
        "/jobs/known-urls",
        json={"urls": ["https://example.com/job-api-1", "https://example.com/unknown"]},
    )
    assert known_resp.status_code == 200
    known_urls = known_resp.json()["known_urls"]
    assert "https://example.com/job-api-1" in known_urls
    assert "https://example.com/unknown" not in known_urls

    # 3. Get recent URLs
    urls_resp = api_client.get("/jobs/urls?source=euraxess")
    assert urls_resp.status_code == 200
    assert "urls" in urls_resp.json()
    assert "https://example.com/job-api-1" in urls_resp.json()["urls"]

    # 4. Get pending details
    pending_resp = api_client.get("/jobs/pending-details?source=euraxess")
    assert pending_resp.status_code == 200
    pending = pending_resp.json()
    assert len(pending) >= 1
    assert pending[0]["url"] == "https://example.com/job-api-1"

    # 5. Update scraped details
    update_resp = api_client.put(
        "/jobs/details",
        json=[
            {
                "url": "https://example.com/job-api-1",
                "job_details": "## AI PhD Description\n\nFull details of the position.",
            }
        ],
    )
    assert update_resp.status_code == 200

    # 6. Verify checkpoint endpoints are removed (404)
    checkpoint_resp = api_client.get("/jobs/checkpoint?source=euraxess")
    assert checkpoint_resp.status_code == 404
