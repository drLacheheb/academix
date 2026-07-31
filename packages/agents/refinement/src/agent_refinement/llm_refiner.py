import json
import logging
import os

from core.domain.interfaces.refiners import BaseRefiner
from core.domain.interfaces.services import BaseLlmRunner
from core.domain.models.schemas import (
    CandidateCvExtraction,
    JobRefinementExtraction,
    RefinementResult,
)
from core.infrastructure.logging.logger import get_logger


class LlmRefiner(BaseRefiner):
    def __init__(
        self,
        runner: BaseLlmRunner,
        max_input_tokens: int = 6000,
        max_output_tokens: int = 2000,
        logger: logging.Logger | None = None,
    ):
        self._runner = runner
        self._max_input_tokens = max_input_tokens
        self._max_output_tokens = max_output_tokens
        self._max_input_chars = max_input_tokens * 4
        self.logger = logger or get_logger("refinement-llm-refiner")

        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "refinement_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

        cv_prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "cv_extraction_prompt.txt"
        )
        with open(cv_prompt_path, "r", encoding="utf-8") as f:
            self._cv_system_prompt = f.read().strip()

    @property
    def is_loaded(self) -> bool:
        return self._runner.is_loaded

    def load_model(self) -> None:
        self._runner.load_model()

    def free_model(self) -> None:
        self._runner.free_model()

    def refine(
        self,
        url: str,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> RefinementResult:
        extracted = self._run_inference(title, location, description, requirements)

        required_skills = extracted.get("required_skills", [])
        if not isinstance(required_skills, list):
            required_skills = []

        education_level = extracted.get("education_level")
        if not isinstance(education_level, str):
            education_level = None

        city = extracted.get("city")
        if not isinstance(city, str):
            city = None

        country = extracted.get("country")
        if not isinstance(country, str):
            country = None

        return RefinementResult(
            url=url,
            required_skills=required_skills,
            education_level=education_level,
            city=city,
            country=country,
        )

    def refine_cv(self, text: str) -> dict:
        truncated_text = text[: self._max_input_chars]

        try:
            cv_schema = CandidateCvExtraction.model_json_schema()
            response_text = self._runner.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._cv_system_prompt},
                    {
                        "role": "user",
                        "content": f"Candidate CV Text:\n\n{truncated_text}",
                    },
                ],
                max_tokens=self._max_output_tokens,
                response_format={"type": "json_object", "schema": cv_schema},
            )
            if response_text:
                parsed = self._parse_json_response(response_text.strip())
                validated = CandidateCvExtraction.model_validate(parsed)
                return validated.model_dump()
            raise RuntimeError("LLM service returned empty completion response")
        except Exception as e:
            self.logger.error(f"GGUF CV inference failed: {e}")
            raise RuntimeError(f"GGUF CV inference failed: {e}") from e

    def _run_inference(
        self,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> dict:
        text = self._build_input_text(title, location, description, requirements)

        try:
            job_schema = JobRefinementExtraction.model_json_schema()
            response_text = self._runner.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=self._max_output_tokens,
                response_format={"type": "json_object", "schema": job_schema},
            )

            if response_text:
                parsed = self._parse_json_response(response_text.strip())
                validated = JobRefinementExtraction.model_validate(parsed)
                return validated.model_dump()
            raise RuntimeError("LLM service returned empty completion response")
        except Exception as e:
            self.logger.error(f"GGUF inference failed: {e}")
            raise RuntimeError(f"GGUF inference failed: {e}") from e

    def _build_input_text(
        self,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> str:
        title_block = f"Title: {title}\n"
        loc_block = f"Location: {location}\n" if location else ""

        # Calculate available budget for desc and req
        avail_budget = self._max_input_chars - len(title_block) - len(loc_block) - 100
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

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        text = raw.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()

        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    pass
            raise
