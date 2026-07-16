import json
import os
import sys

from core.domain.interfaces.refiners import BaseRefiner
from core.domain.models.schemas import RefinementResult


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

    def _run_inference(
        self,
        title: str,
        location: str | None,
        description: str | None,
        requirements: str | None,
    ) -> dict:
        import onnxruntime_genai as og

        text = self._build_input_text(title, location, description, requirements)
        if "gemma" in self._model_path.lower():
            prompt = f"<start_of_turn>system\n{self._system_prompt}<end_of_turn>\n<start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model\n"
        else:
            prompt = f"<|system|>\n{self._system_prompt}<|end|>\n<|user|>\n{text} <|end|>\n<|assistant|>\n"

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
                req_str = req_str[:avail_budget - len(desc_str)]
            elif len(req_str) <= half_budget:
                desc_str = desc_str[:avail_budget - len(req_str)]
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
