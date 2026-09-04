"""
The model-backend contract.

Every backend (mock, vLLM, anything else later) must implement this interface.
The rest of the app depends only on `ModelBackend` — never on a concrete
backend — so backends can be swapped via config without changing app code.
This is the seam that lets us develop against a mock locally and point at real
vLLM later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: str      # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResult:
    """What a backend returns for a chat request."""
    content: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ModelBackend(ABC):
    """
    The contract. A backend is anything that can take a list of chat messages
    and return a completion. Concrete backends implement `generate`.
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> ChatResult:
        """Take messages, return a completion. Must be implemented by subclasses."""
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the backend is ready to serve. Used by readiness checks."""
        raise NotImplementedError
