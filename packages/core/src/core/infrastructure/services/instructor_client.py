import os
from typing import TypeVar

import instructor
from core.domain.interfaces.llm import LlmClient
from core.infrastructure.logging.logger import get_logger
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

logger = get_logger("core-instructor-client")

T = TypeVar("T", bound=BaseModel)


class InstructorLlmClient(LlmClient):
    def __init__(
        self,
        model_name: str = "hf.co/unsloth/gemma-4-E2B-it-GGUF:Q4_K_M",
        base_url: str | None = None,
        temperature: float = 0.0,
    ):
        self.model_name = os.environ.get("LLM_MODEL", model_name)
        url = base_url or os.environ.get("LLM_SERVICE_URL", "http://localhost:11434/v1")
        url = url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"

        self.base_url = url
        self.temperature = temperature

        timeout_seconds = float(os.environ.get("LLM_TIMEOUT", "120.0"))
        sdk_retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))

        self._raw_client = OpenAI(
            base_url=self.base_url,
            api_key=os.environ.get("LLM_API_KEY", "ollama"),
            timeout=timeout_seconds,
            max_retries=sdk_retries,
        )
        self._instructor_client = instructor.from_openai(
            self._raw_client,
            mode=instructor.Mode.JSON,
        )

    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: type[T],
        max_tokens: int = 8192,
        max_retries: int = 3,
    ) -> T:
        try:
            return self._instructor_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_model=response_model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                max_retries=max_retries,
            )
        except Exception as ex:
            logger.error(
                f"Instructor completion error for model {response_model.__name__} "
                f"at {self.base_url}: {ex}"
            )
            raise RuntimeError(f"LLM completion failed for {response_model.__name__}: {ex}") from ex
