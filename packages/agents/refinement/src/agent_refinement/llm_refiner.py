import json
import logging
import os

from core.domain.interfaces.refiners import BaseRefiner
from core.domain.models.schemas import RefinementResult


class LlmRefiner(BaseRefiner):
    def __init__(
        self,
        model_path: str,
        models_dir: str = "models",
        max_length: int = 4096,
        temperature: float = 0.0,
        max_text_chars: int = 3000,
        logger: logging.Logger | None = None,
    ):
        self._model_path = model_path
        self._models_dir = models_dir
        self._max_length = max_length
        self._temperature = temperature
        self._max_text_chars = max_text_chars
        self._model = None
        self.logger = logger or logging.getLogger("agent.refinement.refiner")

        # Resolve Hugging Face path format or local file path
        # Example format: repo_id/filename.gguf -> unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf
        self._repo_id = None
        self._filename = None
        self._resolved_model_path = model_path

        if "/" in model_path and model_path.endswith(".gguf"):
            parts = model_path.split("/")
            if len(parts) >= 3:
                self._repo_id = "/".join(parts[:-1])
                self._filename = parts[-1]
                self._resolved_model_path = os.path.abspath(
                    os.path.join(models_dir, model_path)
                )

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "refinement_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

        cv_prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "cv_extraction_prompt.txt"
        )
        with open(cv_prompt_path, "r", encoding="utf-8") as f:
            self._cv_system_prompt = f.read().strip()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load_model(self) -> None:
        from llama_cpp import Llama

        # Check if resolved path exists, download if not and repo info is available
        if not os.path.exists(self._resolved_model_path):
            if self._repo_id and self._filename:
                self.logger.info(
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

        self.logger.info(f"Loading GGUF model from {self._resolved_model_path}...")
        self._model = Llama(
            model_path=self._resolved_model_path,
            n_ctx=self._max_length,
            n_threads=os.cpu_count(),
            verbose=False,
        )
        self.logger.info("Model loaded successfully!")

    def free_model(self) -> None:
        if self._model is not None:
            self.logger.info("Freeing model from memory...")
            del self._model
            self._model = None
            import gc
            gc.collect()
            self.logger.info("Model freed successfully!")

    def refine(
        self,
        url: str,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> RefinementResult:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not description and not requirements:
            return RefinementResult(
                url=url,
                required_skills=[],
                education_level=None,
                city=None,
                country=None,
            )

        extracted = self._run_inference(title, location, description, requirements)

        required_skills = extracted.get("required_skills", [])
        education_level = extracted.get("education_level")
        city = extracted.get("city")
        country = extracted.get("country")

        return RefinementResult(
            url=url,
            required_skills=required_skills,
            education_level=education_level,
            city=city,
            country=country,
        )

    def refine_cv(self, text: str) -> dict:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Truncate input text to max length of chars
        truncated_text = text[:self._max_text_chars]

        try:
            response = self._model.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._cv_system_prompt},
                    {"role": "user", "content": f"Candidate CV Text:\n\n{truncated_text}"},
                ],
                max_tokens=2048,
                temperature=self._temperature,
            )
            raw_output = response["choices"][0]["message"]["content"].strip()
            return self._parse_json_response(raw_output)
        except Exception as e:
            self.logger.warning(f"GGUF CV inference failed: {e}")
            return {}

    def _run_inference(
        self,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> dict:
        text = self._build_input_text(title, location, description, requirements)

        try:
            response = self._model.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=1024,
                temperature=self._temperature,
            )
            raw_output = response["choices"][0]["message"]["content"].strip()
            return self._parse_json_response(raw_output)
        except Exception as e:
            self.logger.warning(f"GGUF inference failed: {e}")
            return {}

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
        avail_budget = self._max_text_chars - len(title_block) - len(loc_block) - 100
        if avail_budget < 500:
            avail_budget = 500

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
