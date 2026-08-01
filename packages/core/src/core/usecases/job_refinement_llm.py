import os

from openai.types.chat import ChatCompletionMessageParam

from core.domain.interfaces.llm import LlmClient
from core.domain.models.schemas import JobRefinementExtraction, RefinementResult
from core.infrastructure.logging.logger import get_logger

logger = get_logger("usecase-refine-job")


class RefineJobUseCase:
    def __init__(self, llm: LlmClient, max_output_tokens: int = 2000):
        self._llm = llm
        self._max_output_tokens = max_output_tokens

        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "refinement_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def execute(
        self,
        url: str,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
        max_input_chars: int = 24000,
    ) -> RefinementResult:
        input_text = self._build_input_text(
            title, location, description, requirements, max_input_chars
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": input_text},
        ]
        extracted: JobRefinementExtraction = self._llm.complete(
            messages=messages,
            response_model=JobRefinementExtraction,
            max_tokens=self._max_output_tokens,
        )

        return RefinementResult(
            url=url,
            required_skills=extracted.required_skills or [],
            education_level=extracted.education_level,
            city=extracted.city,
            country=extracted.country,
        )

    def _build_input_text(
        self,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
        max_input_chars: int,
    ) -> str:
        title_block = f"Title: {title}\n"
        loc_block = f"Location: {location}\n" if location else ""

        avail_budget = max_input_chars - len(title_block) - len(loc_block) - 100
        avail_budget = max(avail_budget, 500)

        desc_str = description or ""
        req_str = requirements or ""

        if len(desc_str) + len(req_str) > avail_budget:
            half_budget = avail_budget // 2
            if len(desc_str) <= half_budget:
                req_str = req_str[: avail_budget - len(desc_str)]
            elif len(req_str) <= half_budget:
                desc_str = desc_str[: avail_budget - len(req_str)]
            else:
                desc_str = desc_str[:half_budget]
                req_str = req_str[:half_budget]

        desc_block = f"Description:\n{desc_str}\n" if desc_str else ""
        req_block = f"Requirements:\n{req_str}\n" if req_str else ""

        return title_block + loc_block + desc_block + req_block
