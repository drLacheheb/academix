from abc import ABC, abstractmethod
from typing import TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[ChatCompletionMessageParam],
        response_model: type[T],
        max_tokens: int = 2048,
    ) -> T:
        pass
