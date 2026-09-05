"""
Adapter that plugs the standalone llm-guardrails-gateway into this app's
Guardrails interface.

It imports the *real* check_input / check_output from that separate project and
translates their return shapes into our GuardrailResult. The gateway stays an
independent repo; this wrapper just calls into it.

The gateway loads policy.yaml via a relative path (it assumes it runs from its
own folder), so we temporarily chdir into the gateway folder while importing.

Graceful by design: if the gateway path isn't configured or its dependencies
(Presidio/spaCy) aren't installed, this falls back to allowing everything, so
the app still runs for anyone who clones it without the gateway.
"""

import contextlib
import importlib
import os
import sys


from app.backends.base import ChatMessage
from app.pipeline.guardrails import GuardrailResult, Guardrails


@contextlib.contextmanager
def _in_dir(path: str):
    """Temporarily switch working directory (so gateway's relative paths work)."""
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


class GatewayGuardrails(Guardrails):
    """Wraps the external llm-guardrails-gateway. Falls back to passthrough."""

    def __init__(self, gateway_path: str):
        self._ok = False
        self._check_input = None
        self._check_output = None
        self._gateway_path = gateway_path
        self._load(gateway_path)

    def _load(self, gateway_path: str) -> None:
        """Try to import the gateway's guardrail functions from its folder."""
        if not gateway_path or not os.path.isdir(gateway_path):
            print(f"[guardrails] gateway path not found ({gateway_path!r}); "
                  f"falling back to passthrough")
            return
        try:
            # The gateway's files use bare imports (e.g. `from policy import ...`),
            # so its folder must be on sys.path. And it reads policy.yaml by a
            # relative path, so we import from *inside* the gateway folder.
            if gateway_path not in sys.path:
                sys.path.insert(0, gateway_path)
            with _in_dir(gateway_path):
                gateway = importlib.import_module("gateway")
                output_guard = importlib.import_module("output_guard")
            self._check_input = gateway.check_input
            self._check_output = output_guard.check_output
            self._ok = True
            print("[guardrails] llm-guardrails-gateway loaded; real screening active")
        except Exception as exc:  # missing deps, import errors, etc.
            print(f"[guardrails] could not load gateway ({exc!r}); "
                  f"falling back to passthrough")

    @staticmethod
    def _latest_user(messages: list[ChatMessage]) -> str:
        for m in reversed(messages):
            if m.role == "user":
                return m.content
        return ""

    async def check_input(self, messages: list[ChatMessage]) -> GuardrailResult:
        if not self._ok:
            return GuardrailResult(allowed=True)
        text = self._latest_user(messages)
        with _in_dir(self._gateway_path):
            verdict = self._check_input(text)      # returns a GatewayResult
        if verdict.allowed:
            return GuardrailResult(allowed=True)
        reason = "; ".join(verdict.reasons) or "blocked by input guardrail"
        return GuardrailResult(allowed=False, reason=reason)

    async def check_output(self, content: str) -> GuardrailResult:
        if not self._ok:
            return GuardrailResult(allowed=True)
        with _in_dir(self._gateway_path):
            allowed, reasons = self._check_output(content)   # returns (bool, list)
        if allowed:
            return GuardrailResult(allowed=True)
        reason = "; ".join(reasons) or "blocked by output guardrail"
        return GuardrailResult(allowed=False, reason=reason)
