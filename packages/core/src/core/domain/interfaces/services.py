from abc import ABC, abstractmethod
from collections.abc import Sequence


class BaseEmbeddingService(ABC):
    @abstractmethod
    def encode_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def encode_research(self, interests: list[str] | None, title: str = "") -> list[float] | None:
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
        messages: Sequence[dict[str, str]],
        max_tokens: int = 512,
        response_format: dict | None = None,
    ) -> str:
        pass


class BaseStorageService(ABC):
    @abstractmethod
    def upload(self, filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    def get_local_path(self, uri: str) -> tuple[str, bool]:
        pass

    @abstractmethod
    def clean_up(self, local_path: str) -> None:
        pass

    @abstractmethod
    def verify_connection(self) -> None:
        pass
