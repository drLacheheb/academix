from abc import ABC, abstractmethod


class BaseEmbeddingService(ABC):
    @abstractmethod
    def encode_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def encode_research(self, interests: list[str] | None, title: str = "") -> list[float] | None:
        pass

    @abstractmethod
    def encode_degree(self, fields: list[str] | None) -> list[float] | None:
        pass


class BaseLanguageDetector(ABC):
    @abstractmethod
    def detect_lang(self, text: str) -> str:
        pass


class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str) -> tuple[str, bool]:
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
    def delete(self, uri: str) -> None:
        pass

    @abstractmethod
    def verify_connection(self) -> None:
        pass
