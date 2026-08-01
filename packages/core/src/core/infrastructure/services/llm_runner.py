import gc
import os
from collections.abc import Sequence

from core.domain.interfaces.services import BaseLlmRunner
from core.infrastructure.logging.logger import get_logger

logger = get_logger("core-llm-runner")


class LocalLlmRunner(BaseLlmRunner):
    def __init__(
        self,
        model_path: str,
        models_dir: str = "models",
        max_context: int = 8192,
        temperature: float = 0.0,
    ):
        self.model_path = model_path
        self.models_dir = models_dir
        self.max_context = max_context
        self.temperature = temperature
        self.model = None

        self._repo_id = None
        self._filename = None
        self._resolved_path = model_path

        # Resolve Hugging Face path formats (e.g. repo/name/file.gguf)
        if "/" in model_path and model_path.endswith(".gguf"):
            parts = model_path.split("/")
            if len(parts) >= 3:
                self._repo_id = "/".join(parts[:-1])
                self._filename = parts[-1]
                self._resolved_path = os.path.abspath(os.path.join(models_dir, model_path))

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load_model(self) -> None:
        if self.model is not None:
            return

        from llama_cpp import Llama

        if not os.path.exists(self._resolved_path):
            if self._repo_id and self._filename:
                logger.info(
                    f"Model file not found locally. Downloading {self._filename} "
                    f"from HF repo {self._repo_id}..."
                )
                target_dir = os.path.dirname(self._resolved_path)
                os.makedirs(target_dir, exist_ok=True)
                from huggingface_hub import hf_hub_download

                hf_hub_download(
                    repo_id=self._repo_id,
                    filename=self._filename,
                    local_dir=target_dir,
                )
            else:
                raise FileNotFoundError(f"Model path does not exist: {self._resolved_path}")

        n_gpu_layers = int(os.environ.get("N_GPU_LAYERS", "0"))
        cpu_cores = os.cpu_count() or 4
        logger.info(
            f"Loading local GGUF model from {self._resolved_path} "
            f"(threads: {cpu_cores}, n_gpu_layers: {n_gpu_layers})..."
        )
        self.model = Llama(
            model_path=self._resolved_path,
            n_ctx=self.max_context,
            n_batch=1024,
            n_threads=cpu_cores,
            n_threads_batch=cpu_cores,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )
        logger.info("Local GGUF model loaded successfully!")


    def free_model(self) -> None:
        if self.model is not None:
            logger.info("Freeing GGUF model from memory...")
            try:
                self.model.close()
            except Exception:
                pass
            del self.model
            self.model = None
            gc.collect()
            logger.info("GGUF model memory freed successfully!")

    def create_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        self.load_model()
        if self.model is None:
            raise RuntimeError("Llama model failed to load.")

        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format

        chat_messages: list = list(messages)
        response = self.model.create_chat_completion(
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            stop=["```"],
            **kwargs,
        )

        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message", {})
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        return content.strip()
        return ""


class OnnxLlmRunner(BaseLlmRunner):
    def __init__(
        self,
        model_path: str = "sizzlebop/gemma-4-E2B-text-only-onnx-int4",
        models_dir: str = "models",
        max_context: int = 8192,
        temperature: float = 0.0,
    ):
        self.model_path = model_path
        self.models_dir = models_dir
        self.max_context = max_context
        self.temperature = temperature
        self.embed_session = None
        self.decoder_session = None
        self.tokenizer = None

        self._resolved_path = (
            os.path.abspath(os.path.join(models_dir, model_path))
            if not os.path.isabs(model_path)
            else model_path
        )

    @property
    def is_loaded(self) -> bool:
        return self.embed_session is not None and self.decoder_session is not None

    def load_model(self) -> None:
        if self.is_loaded:
            return

        import onnxruntime as ort
        from transformers import AutoTokenizer

        if not os.path.exists(self._resolved_path):
            logger.info(
                f"ONNX Model directory not found at {self._resolved_path}. "
                f"Downloading sizzlebop/gemma-4-E2B-text-only-onnx-int4..."
            )
            os.makedirs(self._resolved_path, exist_ok=True)
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id="sizzlebop/gemma-4-E2B-text-only-onnx-int4",
                local_dir=self._resolved_path,
            )

        logger.info(f"Loading 2-graph ONNX sessions from {self._resolved_path}...")
        embed_path = os.path.join(self._resolved_path, "onnx", "embed_tokens_q4.onnx")
        decoder_path = os.path.join(self._resolved_path, "onnx", "decoder_model_merged_q4.onnx")

        providers = ["CPUExecutionProvider"]
        self.embed_session = ort.InferenceSession(embed_path, providers=providers)
        self.decoder_session = ort.InferenceSession(decoder_path, providers=providers)
        self.tokenizer = AutoTokenizer.from_pretrained(self._resolved_path)
        logger.info("2-Graph ONNX sessions loaded successfully!")

    def free_model(self) -> None:
        if self.is_loaded:
            logger.info("Freeing ONNX sessions from memory...")
            del self.embed_session
            del self.decoder_session
            del self.tokenizer
            self.embed_session = None
            self.decoder_session = None
            self.tokenizer = None
            gc.collect()
            logger.info("ONNX sessions memory freed successfully!")

    def create_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        self.load_model()
        if not self.is_loaded or self.tokenizer is None:
            raise RuntimeError("2-Graph ONNX sessions failed to load.")

        import numpy as np

        chat_messages = list(messages)
        full_prompt = self.tokenizer.apply_chat_template(
            chat_messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        input_ids = self.tokenizer.encode(full_prompt, return_tensors="np")
        embed_outputs = self.embed_session.run(None, {"input_ids": input_ids})
        inputs_embeds = embed_outputs[0]
        per_layer_inputs = embed_outputs[1]

        seq_len = inputs_embeds.shape[1]
        attention_mask = np.ones((1, seq_len), dtype=np.int64)
        position_ids = np.arange(seq_len, dtype=np.int64).reshape(1, -1)
        num_logits_to_keep = np.array(1, dtype=np.int64)

        decoder_inputs = {
            "inputs_embeds": inputs_embeds,
            "attention_mask": attention_mask,
            "position_ids": position_ids,
            "num_logits_to_keep": num_logits_to_keep,
            "per_layer_inputs": per_layer_inputs,
        }

        # Initialize empty past key values (15 layers)
        for i in range(15):
            head_dim = 512 if i in (4, 9, 14) else 256
            zero_arr = np.zeros((1, 1, 0, head_dim), dtype=np.float32)
            decoder_inputs[f"past_key_values.{i}.key"] = zero_arr
            decoder_inputs[f"past_key_values.{i}.value"] = zero_arr

        output_tokens = []
        for _ in range(max_tokens):
            outputs = self.decoder_session.run(None, decoder_inputs)
            logits = outputs[0]
            next_token_id = int(np.argmax(logits[0, -1, :]))

            if next_token_id == self.tokenizer.eos_token_id:
                break
            output_tokens.append(next_token_id)

            # Update inputs for next token iteration
            next_token_arr = np.array([[next_token_id]], dtype=np.int64)
            embed_outputs = self.embed_session.run(None, {"input_ids": next_token_arr})
            decoder_inputs["inputs_embeds"] = embed_outputs[0]
            decoder_inputs["per_layer_inputs"] = embed_outputs[1]

            attention_mask = np.ones((1, attention_mask.shape[1] + 1), dtype=np.int64)
            position_ids = np.array([[attention_mask.shape[1] - 1]], dtype=np.int64)
            decoder_inputs["attention_mask"] = attention_mask
            decoder_inputs["position_ids"] = position_ids

            # Feed past key value tensors back in
            for i in range(15):
                decoder_inputs[f"past_key_values.{i}.key"] = outputs[1 + i * 2]
                decoder_inputs[f"past_key_values.{i}.value"] = outputs[2 + i * 2]

        return self.tokenizer.decode(output_tokens, skip_special_tokens=True).strip()
