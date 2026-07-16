from abc import ABC, abstractmethod

class BaseHttpClient(ABC):
    @abstractmethod
    def fetch(self, url: str) -> bytes | None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
