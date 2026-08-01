import os

from openai.types.chat import ChatCompletionMessageParam

from core.domain.interfaces.llm import LlmClient
from core.domain.models.schemas import CandidateCvExtraction
from core.infrastructure.logging.logger import get_logger

logger = get_logger("usecase-extract-cv")


class ExtractCvUseCase:
    def __init__(self, llm: LlmClient, max_output_tokens: int = 2000):
        self._llm = llm
        self._max_output_tokens = max_output_tokens

        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "cv_extraction_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def execute(self, text: str, max_input_chars: int = 24000) -> CandidateCvExtraction:
        truncated_text = text[:max_input_chars]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": f"Candidate CV Text:\n\n{truncated_text}"},
        ]
        return self._llm.complete(
            messages=messages,
            response_model=CandidateCvExtraction,
            max_tokens=self._max_output_tokens,
        )
