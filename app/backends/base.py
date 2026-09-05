"""
The model-backend contract.

Every backend (mock, vLLM, anything else later) must implement this interface.
The rest of the app depends only on `ModelBackend` -- never on a concrete
backend -- so backends can be swapped via config without changing app code.
This is the seam that lets us develop against a mock locally and point at real
vLLM later.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str      # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResult:
    """What a backend returns for a non-streaming chat request."""
    content: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ModelBackend(ABC):
    """
    The contract. A backend is anything that can take a list of chat messages
    and either return a completion or stream it token by token.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> ChatResult:
        """Take messages, return a full completion. Non-streaming."""
        raise NotImplementedError

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Take messages, yield the completion in chunks (tokens/words) as they are
        produced. Returns an async iterator of text pieces. Implementations use
        `async def` + `yield` (an async generator).
        """
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the backend is ready to serve. Used by readiness checks."""
        raise NotImplementedError
