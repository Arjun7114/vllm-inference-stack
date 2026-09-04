"""
The application layer.

A FastAPI service that exposes an OpenAI-compatible chat endpoint and forwards
requests to whichever model backend is configured (mock locally, vLLM later).

The request pipeline, in order:
    validate -> auth -> input guardrails -> model call -> output guardrails -> log
Each stage is a distinct, swappable unit. Guardrails default to passthrough;
the llm-guardrails-gateway plugs into that slot later without touching this file.
"""

import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.backends.base import ChatMessage
from app.config import get_backend, settings
from app.pipeline.auth import require_api_key
from app.pipeline.guardrails import get_guardrails
from app.pipeline.logging_setup import get_logger

app = FastAPI(title="vLLM Inference Stack -- App Layer")

# Instances chosen by config, created once for the app's lifetime.
backend = get_backend()
guardrails = get_guardrails()
logger = get_logger()


# ---- Request/response shapes (OpenAI-compatible subset) ----

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[Message] = Field(min_length=1)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user(cls, messages: list[Message]) -> list[Message]:
        if messages[-1].role != "user":
            raise ValueError("the last message must have role 'user'")
        return messages


# ---- Routes ----

@app.get("/health")
async def health():
    """Readiness check (unauthenticated so orchestrators can probe it)."""
    ok = await backend.health()
    return {"status": "ok" if ok else "unavailable", "backend": settings.backend}


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(req: ChatRequest):
    """Run the request through the pipeline and return an OpenAI-shaped reply."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    started = time.perf_counter()

    messages = [ChatMessage(role=m.role, content=m.content) for m in req.messages]

    # --- input guardrails ---
    gate_in = await guardrails.check_input(messages)
    if not gate_in.allowed:
        logger.info("request blocked (input)", extra={"data": {
            "request_id": request_id, "stage": "input_guardrail", "reason": gate_in.reason,
        }})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Blocked by input guardrail: {gate_in.reason}")

    # --- model call ---
    result = await backend.generate(
        messages=messages,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )

    # --- output guardrails ---
    gate_out = await guardrails.check_output(result.content)
    if not gate_out.allowed:
        logger.info("request blocked (output)", extra={"data": {
            "request_id": request_id, "stage": "output_guardrail", "reason": gate_out.reason,
        }})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Blocked by output guardrail: {gate_out.reason}")

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    # --- structured log line ---
    logger.info("request completed", extra={"data": {
        "request_id": request_id,
        "backend": settings.backend,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "latency_ms": elapsed_ms,
        "status": 200,
    }})

    return {
        "id": request_id,
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
