"""
Mock model backend.

Returns canned responses without any GPU or network call, so the entire app
layer — auth, validation, pipeline, logging, streaming — can be built and tested
locally for free. It satisfies the same `ModelBackend` contract as the real
vLLM backend, so the app cannot tell the difference. Swapping to real vLLM later
is a config change, not a code change.
"""

import asyncio

from app.backends.base import ChatMessage, ChatResult, ModelBackend


class MockBackend(ModelBackend):
    """A fake backend for local development. No GPU, no network."""

    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> ChatResult:
        # Grab the last user message to make the canned reply feel responsive.
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )

        # Simulate a tiny bit of "thinking" time so streaming/latency behaviour
        # later feels realistic. Kept short so local dev stays fast.
        await asyncio.sleep(0.05)

        reply = (
            f"[mock reply] You said: '{last_user}'. "
            f"This is a canned response from MockBackend — no GPU involved. "
            f"When pointed at real vLLM, this same call returns Mistral's output."
        )

        # Rough token estimates (word count is fine for a mock).
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        completion_tokens = len(reply.split())

        return ChatResult(
            content=reply,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def health(self) -> bool:
        # A mock is always "ready".
        return True
