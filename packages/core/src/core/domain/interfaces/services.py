from abc import ABC, abstractmethod
from typing import Optional
from core.domain.models.profile import CandidateProfile


class BaseEmbeddingService(ABC):
    @abstractmethod
    def encode_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def encode_research(
        self, interests: Optional[list[str]], title: str = ""
    ) -> Optional[list[float]]:
        pass


class BaseCvExtractor(ABC):
    @abstractmethod
    def extract_profile(self, file_path: str) -> tuple[CandidateProfile, str]:
        pass


class BaseLanguageDetector(ABC):
    @abstractmethod
    def detect_lang(self, text: str) -> str:
        pass


class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str) -> str:
        pass


class BaseLlmRunner(ABC):
    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @abstractmethod
    def load_model(self) -> None:
        pass

    @abstractmethod
    def free_model(self) -> None:
        pass

    @abstractmethod
    def create_chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        response_format: Optional[dict] = None,
    ) -> str:
        pass


class BaseStorageService(ABC):
    @abstractmethod
    def upload(self, filename: str, content: bytes) -> str:
        """Uploads file content and returns its URI or URL string."""
        pass

    @abstractmethod
    def get_local_path(self, uri: str) -> tuple[str, bool]:
        """
        Given a file URI (local path or S3 URL), returns a local file path
        where the content is stored (either directly or downloaded to a temp file).
        
        Returns a tuple of (local_path, is_temporary).
        """
        pass

    @abstractmethod
    def clean_up(self, local_path: str) -> None:
        """Cleans up the local path if it was a temporary file."""
        pass

    @abstractmethod
    def verify_connection(self) -> None:
        """Validates connection to the storage provider backend."""
        pass
