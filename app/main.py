"""
The application layer.

A FastAPI service that exposes an OpenAI-compatible chat endpoint and forwards
requests to whichever model backend is configured (mock locally, vLLM later).
This is the layer that will grow to hold validation, auth, a guardrails slot,
and logging -- the request pipeline. It now enforces input validation and an
API-key check before any request reaches the backend.
"""

import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field, field_validator

from app.backends.base import ChatMessage
from app.config import get_backend, settings
from app.pipeline.auth import require_api_key

app = FastAPI(title="vLLM Inference Stack -- App Layer")

# One backend instance for the app's lifetime, chosen by config (mock or vllm).
backend = get_backend()


# ---- Request/response shapes (OpenAI-compatible subset) ----

class Message(BaseModel):
    # `Literal` restricts role to these exact strings -- anything else is a 422.
    role: Literal["system", "user", "assistant"]
    # `min_length=1` rejects empty content.
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    model: str | None = None
    # `min_length=1` rejects an empty messages list.
    messages: list[Message] = Field(min_length=1)
    # Bounds keep requests sane: 1..4096 tokens, temperature 0..2.
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user(cls, messages: list[Message]) -> list[Message]:
        # A chat request should end with a user turn for the model to answer.
        if messages[-1].role != "user":
            raise ValueError("the last message must have role 'user'")
        return messages


# ---- Routes ----

@app.get("/health")
async def health():
    """Readiness check -- reports whether the backend is ready to serve.

    Left unauthenticated on purpose so load balancers / orchestrators can probe
    readiness without a key.
    """
    ok = await backend.health()
    return {"status": "ok" if ok else "unavailable", "backend": settings.backend}


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat endpoint. Protected by the API-key dependency."""
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
