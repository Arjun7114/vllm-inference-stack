"""
The application layer.

A FastAPI service that exposes an OpenAI-compatible chat endpoint and forwards
requests to whichever model backend is configured (mock locally, vLLM later).
This is the layer that will grow to hold validation, auth, a guardrails slot,
and logging — the request pipeline. Right now it does the core job: accept a
request, call the backend, return the reply.
"""

import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from app.backends.base import ChatMessage
from app.config import get_backend, settings

app = FastAPI(title="vLLM Inference Stack — App Layer")

# One backend instance for the app's lifetime, chosen by config (mock or vllm).
backend = get_backend()


# ---- Request/response shapes (OpenAI-compatible subset) ----

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[Message]
    max_tokens: int = 256
    temperature: float = 0.7


# ---- Routes ----

@app.get("/health")
async def health():
    """Readiness check — reports whether the backend is ready to serve."""
    ok = await backend.health()
    return {"status": "ok" if ok else "unavailable", "backend": settings.backend}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat endpoint. Forwards to the configured backend."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in req.messages]

    result = await backend.generate(
        messages=messages,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )

    # Shape the response like the OpenAI API so any OpenAI client can consume it.
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:16]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model or settings.model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
        },
    }
