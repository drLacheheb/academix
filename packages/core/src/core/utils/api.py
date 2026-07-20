import os
import httpx


def make_api_client(timeout: float = 30.0) -> httpx.Client:
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    api_secret_key = os.environ.get("API_SECRET_KEY", "")
    return httpx.Client(
        base_url=api_url,
        headers={"Authorization": f"Bearer {api_secret_key}"},
        timeout=timeout,
    )
