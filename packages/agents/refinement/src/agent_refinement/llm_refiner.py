import json
import os
import sys

from core.refiners.base import BaseRefiner
from core.models.job import Job


class LlmRefiner(BaseRefiner):

    def __init__(
        self,
        model_path: str,
        max_length: int = 4096,
        temperature: float = 0.0,
        max_text_chars: int = 3000,
    ):
        self._model_path = model_path
        self._max_length = max_length
        self._temperature = temperature
        self._max_text_chars = max_text_chars
        self._model = None
        self._tokenizer = None

        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "refinement_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self._system_prompt = f.read().strip()

    def load_model(self) -> None:
        if not os.path.exists(self._model_path):
            print(
                f"ONNX model directory not found at: {os.path.abspath(self._model_path)}"
            )
            print(
                "Downloading Phi-4-mini ONNX model automatically from Hugging Face (approx. 2.2GB)..."
            )
            try:
                from huggingface_hub import snapshot_download

                local_dir = "phi-4-mini-onnx"
                snapshot_download(
                    repo_id="microsoft/Phi-4-mini-instruct-onnx",
                    allow_patterns="cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/*",
                    local_dir=local_dir,
                    ignore_patterns=["*.git*", "*.md"],
                )
                print("Download complete!")
            except Exception as e:
                print(f"Error downloading model: {e}", file=sys.stderr)
                raise FileNotFoundError(
                    f"Could not load or download ONNX model at: {os.path.abspath(self._model_path)}"
                ) from e

        import onnxruntime_genai as og

        print(f"Loading ONNX model from {self._model_path}...")
        self._model = og.Model(self._model_path)
        self._tokenizer = og.Tokenizer(self._model)
        print("Model loaded successfully!")

    def refine(self, job: Job) -> Job:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not job.description and not job.requirements:
            job.required_skills = []
            job.education_level = None
            return job

        extracted = self._run_inference(job)

        job.required_skills = extracted.get("required_skills", [])
        job.education_level = extracted.get("education_level")

        return job

    def _run_inference(self, job: Job) -> dict:
        import onnxruntime_genai as og

        text = self._build_input_text(job)
        prompt = f"<|system|>\n{self._system_prompt}<|end|>\n<|user|>\n{text}<|end|>\n<|assistant|>\n"

        try:
            tokens = self._tokenizer.encode(prompt)
            params = og.GeneratorParams(self._model)
            params.set_search_options(
                temperature=self._temperature, max_length=self._max_length
            )

            generator = og.Generator(self._model, params)
            generator.append_tokens(tokens)
            while not generator.is_done():
                generator.generate_next_token()

            output_tokens = generator.get_sequence(0)
            raw_output = self._tokenizer.decode(output_tokens[len(tokens) :]).strip()

            return self._parse_json_response(raw_output)
        except Exception as e:
            print(f"  [Warning] LLM inference failed: {e}", file=sys.stderr)
            return {}

    def _build_input_text(self, job: Job) -> str:
        title_block = f"Title: {job.title}\n"
        req_block = f"\nRequirements:\n{job.requirements}" if job.requirements else ""
        desc_block = f"Description:\n{job.description}" if job.description else ""

        budget = self._max_text_chars - len(title_block) - len(req_block)
        if budget > 0 and desc_block:
            desc_block = desc_block[:budget]

        return title_block + desc_block + req_block

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
