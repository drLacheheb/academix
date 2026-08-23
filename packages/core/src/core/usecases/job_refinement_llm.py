import os

from openai.types.chat import ChatCompletionMessageParam

from core.domain.interfaces.llm import LlmClient
from core.domain.models.schemas import JobRefinementExtraction, RefinementResult
from core.infrastructure.logging.logger import get_logger

logger = get_logger("usecase-refine-job")


class RefineJobUseCase:
    def __init__(self, llm: LlmClient, max_output_tokens: int | None = None):
        self._llm = llm
        default_max = int(os.environ.get("MAX_OUTPUT_TOKENS", "8192"))
        self._max_output_tokens = max_output_tokens or default_max

        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "refinement_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def execute(
        self,
        url: str,
        title: str,
        job_details: str | None,
        max_input_chars: int = 24000,
    ) -> RefinementResult:
        input_text = self._build_input_text(title, job_details, max_input_chars)
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
            employer=extracted.employer,
            deadline=extracted.deadline,
            required_skills=extracted.required_skills or [],
            research_interests=extracted.research_interests or [],
            education_level=extracted.education_level,
            degree_fields=extracted.degree_fields or [],
            city=extracted.city,
            country=extracted.country,
        )

    def _build_input_text(
        self,
        title: str,
        job_details: str | None,
        max_input_chars: int,
    ) -> str:
        title_block = f"Title: {title}\n"

        avail_budget = max_input_chars - len(title_block) - 100
        avail_budget = max(avail_budget, 500)

        main_text = job_details or ""
        if len(main_text) > avail_budget:
            main_text = main_text[:avail_budget]

        details_block = f"Job Details:\n{main_text}\n" if main_text else ""

        return title_block + details_block
