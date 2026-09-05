"""
Mock model backend.

Returns canned responses without any GPU or network call, so the entire app
layer -- auth, validation, pipeline, logging, streaming -- can be built and
tested locally for free. It satisfies the same `ModelBackend` contract as the
real vLLM backend, so the app cannot tell the difference. Swapping to real vLLM
later is a config change, not a code change.
"""

import asyncio
from collections.abc import AsyncIterator

from app.backends.base import ChatMessage, ChatResult, ModelBackend


class MockBackend(ModelBackend):
    """A fake backend for local development. No GPU, no network."""

    def _reply_for(self, messages: list[ChatMessage]) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        return (
            f"[mock reply] You said: '{last_user}'. "
            f"This is a canned response from MockBackend -- no GPU involved. "
            f"When pointed at real vLLM, this same call returns Mistral's output."
        )

    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> ChatResult:
        await asyncio.sleep(0.05)  # simulate a little work
        reply = self._reply_for(messages)
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        completion_tokens = len(reply.split())
        return ChatResult(
            content=reply,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Async generator: yields the reply word by word with a small delay, so the
        streaming behaviour is visible. Each `yield` hands one chunk to the caller
        and pauses until the caller asks for the next.
        """
        reply = self._reply_for(messages)
        for word in reply.split():
            await asyncio.sleep(0.04)   # simulate token-by-token generation
            yield word + " "

    async def health(self) -> bool:
        return True
