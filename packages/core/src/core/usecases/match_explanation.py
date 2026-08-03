import os

from openai.types.chat import ChatCompletionMessageParam

from core.domain.interfaces.llm import LlmClient
from core.domain.models.job import Job
from core.domain.models.profile import CandidateProfile
from core.domain.models.schemas import MatchExplanationExtraction
from core.infrastructure.logging.logger import get_logger

logger = get_logger("usecase-match-explanation")


class ExplainMatchUseCase:
    def __init__(self, llm: LlmClient, max_output_tokens: int = 1024):
        self._llm = llm
        self._max_output_tokens = max_output_tokens

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "match_explanation_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def execute(self, candidate: CandidateProfile, job: Job) -> str:
        user_content = (
            f"Candidate Profile\n"
            f"- Name: {candidate.name}\n"
            f"- Highest Degree: {candidate.highest_degree or 'None'}\n"
            f"- Skills: {', '.join(candidate.skills or [])}\n"
            f"- Research Interests: {', '.join(candidate.research_interests or [])}\n\n"
            f"Job Details\n"
            f"- Title: {job.title}\n"
            f"- Required Skills: {', '.join(job.required_skills or [])}\n"
            f"- Education Requirement: {job.education_level or 'None'}\n\n"
            f"Extract structured key matching reasons for {candidate.name} and this job."
        )

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        validated: MatchExplanationExtraction = self._llm.complete(
            messages=messages,
            response_model=MatchExplanationExtraction,
            max_tokens=self._max_output_tokens,
        )
        if not validated.reasons:
            raise ValueError(
                f"LLM returned zero matching reasons for candidate {candidate.name} "
                f"and job {job.title}"
            )
        return " ".join(r.description for r in validated.reasons)
