import json
import logging
import os
from core.domain.models.profile import CandidateProfile
from core.domain.interfaces.services import BaseCvExtractor, BaseLlmRunner
from core.infrastructure.services.pdf_parser import (
    parse_pdf_to_markdown,
    truncate_bibliography,
)

logger = logging.getLogger(__name__)


class CvExtractor(BaseCvExtractor):
    def __init__(self, runner: BaseLlmRunner):
        self._runner = runner

        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "cv_extraction_prompt.txt",
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def extract_profile(self, file_path: str) -> tuple[CandidateProfile, str]:
        # Step 1: Parse CV to full Markdown using Docling
        raw_markdown = parse_pdf_to_markdown(file_path)

        # Step 2: Truncate long publications bibliography to save token space
        truncated_markdown = truncate_bibliography(raw_markdown)

        # Step 3: Run local Gemma-4 extraction
        try:
            raw_response = self._runner.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {
                        "role": "user",
                        "content": f"Candidate CV Text:\n\n{truncated_markdown}",
                    },
                ],
                max_tokens=2048,
            )
            logger.info("Received raw response from Gemma-4")

            # Clean raw response if it is wrapped in markdown ticks
            cleaned_response = raw_response
            if cleaned_response.startswith("```"):
                # Remove starting markdown block e.g. ```json or ```
                lines = cleaned_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_response = "\n".join(lines).strip()

            parsed_data = json.loads(cleaned_response)
            parsed_data["cv_file_path"] = os.path.basename(file_path)
            parsed_data["raw_text"] = raw_markdown

            profile = CandidateProfile.from_dict(parsed_data)
            return profile, raw_markdown
        except Exception as e:
            logger.error(f"Error during CV metadata extraction: {e}")
            raise
        finally:
            self._runner.free_model()
