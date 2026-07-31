import os
from collections.abc import Sequence

import httpx
from core.domain.interfaces.services import BaseLlmRunner
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-http-runner")


class HttpLlmRunner(BaseLlmRunner):
    """Lightweight HTTP client implementing BaseLlmRunner that delegates

    completion calls to the Centralized LLM Runner Service.
    """

    def __init__(
        self,
        service_url: str | None = None,
        timeout: float = 600.0,
    ):

        self._service_url = service_url or os.environ.get(
            "LLM_SERVICE_URL", "http://localhost:8001"
        )
        self._service_url = self._service_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=self._timeout)

    @property
    def is_loaded(self) -> bool:
        try:
            resp = self._client.get(f"{self._service_url}/health")
            if resp.status_code == 200:
                return resp.json().get("status") == "ok"
            return False
        except Exception:
            return False

    def load_model(self) -> None:
        # Service handles lazy loading automatically on request
        pass

    def free_model(self) -> None:
        # Service handles idle unloading automatically
        pass

    def create_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        url = f"{self._service_url}/v1/chat/completions"
        payload = {
            "messages": list(messages),
            "max_tokens": max_tokens,
            "response_format": response_format,
        }

        resp = self._client.post(url, json=payload)
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message", {})
            if isinstance(msg, dict):
                return str(msg.get("content", ""))
        return ""

    def close(self) -> None:
        self._client.close()
