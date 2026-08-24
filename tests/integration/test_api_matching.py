from fastapi.testclient import TestClient


def test_api_matching_queue_flow(api_client: TestClient):
    # 1. Claim when empty
    claim_resp = api_client.post("/matches/claim", json={"agent_name": "match-worker-1"})
    assert claim_resp.status_code == 200
    assert claim_resp.json()["task"] is None

    # 2. Complete task
    complete_resp = api_client.put(
        "/matches/complete",
        json={
            "task_id": 1,
            "matches": [
                {
                    "candidate_id": 1,
                    "job_url": "https://example.com/job-1",
                    "score": 0.89,
                    "degree_eligible": True,
                    "skill_score": 0.95,
                    "research_score": 0.85,
                }
            ],
        },
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"
