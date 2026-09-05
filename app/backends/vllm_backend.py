"""
Real vLLM backend.

Implements the same ModelBackend contract as MockBackend, but talks to a live
vLLM OpenAI-compatible server over HTTP. Because it satisfies the same contract,
the app doesn't change -- setting BACKEND=vllm swaps the mock for this without
touching any endpoint code.

vLLM exposes:
  GET  /health                 -> readiness
  POST /v1/chat/completions    -> chat (supports stream=true for SSE)
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.backends.base import ChatMessage, ChatResult, ModelBackend


class VLLMBackend(ModelBackend):
    """Talks to a real vLLM server over its OpenAI-compatible API."""

    def __init__(self, base_url: str, model_name: str):
        self._base_url = base_url.rstrip("/")
        self._model = model_name

    def _payload(self, messages, max_tokens, temperature, stream):
        return {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

    async def generate(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> ChatResult:
        url = f"{self._base_url}/v1/chat/completions"
        body = self._payload(messages, max_tokens, temperature, stream=False)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ChatResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url}/v1/chat/completions"
        body = self._payload(messages, max_tokens, temperature, stream=True)
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[len("data: "):]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        piece = chunk["choices"][0]["delta"].get("content", "")
                        if piece:
                            yield piece
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def health(self) -> bool:
        url = f"{self._base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False
