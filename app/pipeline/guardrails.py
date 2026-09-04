"""
Guardrails stage of the request pipeline.

This is the *seam* where input/output safety screening plugs in. It defines a
small contract (`Guardrails`) and a default `PassthroughGuardrails` that allows
everything. The chat endpoint runs the configured guardrails before and after
the model call.

Today the default does nothing. Later, the llm-guardrails-gateway drops into this
slot by providing an implementation of `Guardrails` — no change to the endpoint
or the rest of the app. Building the empty seam now is what makes that later
integration a one-line swap instead of surgery.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.backends.base import ChatMessage


@dataclass
class GuardrailResult:
    """Outcome of a guardrail check."""
    allowed: bool
    reason: str = ""


class Guardrails(ABC):
    """Contract for a guardrails implementation."""

    @abstractmethod
    async def check_input(self, messages: list[ChatMessage]) -> GuardrailResult:
        """Screen the incoming messages before they reach the model."""
        raise NotImplementedError

    @abstractmethod
    async def check_output(self, content: str) -> GuardrailResult:
        """Screen the model's generated output before returning it."""
        raise NotImplementedError


class PassthroughGuardrails(Guardrails):
    """Default: allow everything. Replaced by real guardrails later."""

    async def check_input(self, messages: list[ChatMessage]) -> GuardrailResult:
        return GuardrailResult(allowed=True)

    async def check_output(self, content: str) -> GuardrailResult:
        return GuardrailResult(allowed=True)


def get_guardrails() -> Guardrails:
    """
    Return the configured guardrails. Single place that decides which
    implementation is active — mirrors get_backend(). For now, always passthrough.
    """
    return PassthroughGuardrails()
