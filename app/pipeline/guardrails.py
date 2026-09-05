"""
Guardrails stage of the request pipeline.

This is the *seam* where input/output safety screening plugs in. It defines a
small contract (`Guardrails`) and a default `PassthroughGuardrails` that allows
everything. The chat endpoint runs the configured guardrails before and after
the model call.

Which implementation is active is decided by config: if a gateway path is set,
the external llm-guardrails-gateway is wrapped in; otherwise passthrough. The
endpoint never changes -- this is the one-line swap the seam was built for.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.backends.base import ChatMessage
from app.config import settings


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
    """Default: allow everything. Used when no gateway is configured."""

    async def check_input(self, messages: list[ChatMessage]) -> GuardrailResult:
        return GuardrailResult(allowed=True)

    async def check_output(self, content: str) -> GuardrailResult:
        return GuardrailResult(allowed=True)


def get_guardrails() -> Guardrails:
    """
    Return the configured guardrails. If a gateway path is set, wrap the external
    llm-guardrails-gateway; otherwise passthrough. Mirrors get_backend().
    """
    if settings.guardrails_gateway_path:
        # Imported lazily so passthrough users don't need the gateway's deps.
        from app.pipeline.gateway_guardrails import GatewayGuardrails
        return GatewayGuardrails(settings.guardrails_gateway_path)
    return PassthroughGuardrails()
