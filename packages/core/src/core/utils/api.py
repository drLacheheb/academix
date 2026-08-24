import os

import httpx


def make_api_client(timeout: float = 30.0) -> httpx.Client:
    port = os.environ.get("PORT", "8000")
    api_url = os.environ.get("API_URL", "").strip()

    if not api_url or "localhost:8000" in api_url or "127.0.0.1:8000" in api_url:
        api_url = f"http://127.0.0.1:{port}"

    api_secret_key = os.environ.get("API_SECRET_KEY", "")
    return httpx.Client(
        base_url=api_url,
        headers={"Authorization": f"Bearer {api_secret_key}"},
        timeout=timeout,
    )
