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
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        print(f"Loading Hugging Face model/tokenizer from {self._model_path}...")
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_path)
        
        # Load in bfloat16 for CPU memory and compute efficiency
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_path,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True
        )
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
        import torch

        text = self._build_input_text(title, location, description, requirements)
        if "gemma" in self._model_path.lower():
            prompt = f"<start_of_turn>system\n{self._system_prompt}<end_of_turn>\n<start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model\n"
        else:
            prompt = f"<|system|>\n{self._system_prompt}<|end|>\n<|user|>\n{text} <|end|>\n<|assistant|>\n"

        try:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            with torch.no_grad():
                output_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    do_sample=self._temperature > 0.0,
                    temperature=self._temperature if self._temperature > 0.0 else None,
                    eos_token_id=self._tokenizer.eos_token_id,
                    pad_token_id=self._tokenizer.pad_token_id if self._tokenizer.pad_token_id is not None else self._tokenizer.eos_token_id,
                )
            
            # Slice only the newly generated tokens
            generated_ids = output_ids[0][inputs.input_ids.shape[1]:]
            raw_output = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

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
