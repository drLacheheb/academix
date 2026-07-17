import json
import logging
import os
from typing import Optional
from core.domain.models.profile import CandidateProfile
from core.utils.pdf_parser import parse_pdf_to_markdown, truncate_bibliography

logger = logging.getLogger(__name__)


class CvExtractor:
    def __init__(
        self,
        model_path: Optional[str] = None,
        models_dir: str = "models",
        max_length: int = 4096,
        temperature: float = 0.0,
    ):
        self._model_path = model_path or os.getenv(
            "MODEL_PATH", "unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf"
        )
        self._models_dir = models_dir
        self._max_length = max_length
        self._temperature = temperature
        self._model = None

        # Resolve Hugging Face path format or local file path
        self._repo_id = None
        self._filename = None
        self._resolved_model_path = self._model_path

        if "/" in self._model_path and self._model_path.endswith(".gguf"):
            parts = self._model_path.split("/")
            if len(parts) >= 3:
                self._repo_id = "/".join(parts[:-1])
                self._filename = parts[-1]
                self._resolved_model_path = os.path.abspath(
                    os.path.join(models_dir, self._model_path)
                )

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "cv_extraction_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def _load_model(self):
        from llama_cpp import Llama

        if not os.path.exists(self._resolved_model_path):
            if self._repo_id and self._filename:
                logger.info(
                    f"Model file not found locally. Downloading {self._filename} from HF repo {self._repo_id}..."
                )
                target_dir = os.path.dirname(self._resolved_model_path)
                os.makedirs(target_dir, exist_ok=True)
                from huggingface_hub import hf_hub_download

                hf_hub_download(
                    repo_id=self._repo_id,
                    filename=self._filename,
                    local_dir=target_dir,
                )
            else:
                raise FileNotFoundError(
                    f"Model path does not exist and cannot be auto-downloaded: {self._resolved_model_path}"
                )

        logger.info(
            f"Loading GGUF model for CV extraction from {self._resolved_model_path}..."
        )
        self._model = Llama(
            model_path=self._resolved_model_path,
            n_ctx=self._max_length,
            n_threads=os.cpu_count(),
            verbose=False,
        )

    def _free_model(self):
        if self._model is not None:
            logger.info("Freeing GGUF model from memory...")
            del self._model
            self._model = None
            import gc

            gc.collect()

    def extract_profile(self, file_path: str) -> tuple[CandidateProfile, str]:
        # Step 1: Parse CV to full Markdown using Docling
        raw_markdown = parse_pdf_to_markdown(file_path)

        # Step 2: Truncate long publications bibliography to save token space
        truncated_markdown = truncate_bibliography(raw_markdown)

        # Step 3: Run local Gemma-4 extraction
        self._load_model()
        try:
            response = self._model.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {
                        "role": "user",
                        "content": f"Candidate CV Text:\n\n{truncated_markdown}",
                    },
                ],
                temperature=self._temperature,
                max_tokens=2048,
            )
            raw_response = response["choices"][0]["message"]["content"].strip()
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
            self._free_model()
