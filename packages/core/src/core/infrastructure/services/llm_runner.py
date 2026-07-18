import gc
import logging
import os
from typing import Optional
from core.domain.interfaces.services import BaseLlmRunner

logger = logging.getLogger(__name__)


class LocalLlmRunner(BaseLlmRunner):
    def __init__(
        self,
        model_path: str,
        models_dir: str = "models",
        max_context: int = 4096,
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
                self._resolved_path = os.path.abspath(
                    os.path.join(models_dir, model_path)
                )

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
                    f"Model file not found locally. Downloading {self._filename} from HF repo {self._repo_id}..."
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
                raise FileNotFoundError(
                    f"Model path does not exist and cannot be auto-downloaded: {self._resolved_path}"
                )

        logger.info(f"Loading local GGUF model from {self._resolved_path}...")
        self.model = Llama(
            model_path=self._resolved_path,
            n_ctx=self.max_context,
            n_threads=os.cpu_count(),
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
        messages: list[dict],
        max_tokens: int = 512,
        response_format: Optional[dict] = None,
    ) -> str:
        self.load_model()

        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format

        response = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            **kwargs,
        )
        return response["choices"][0]["message"]["content"].strip()
