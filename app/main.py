"""
The application layer.

FastAPI service exposing an OpenAI-compatible chat endpoint over a swappable
backend (mock/vLLM). Pipeline order:
    validate -> auth -> input guardrails -> model -> output guardrails -> log

Security observability (Option A): every guardrail hit emits a structured
SecurityEvent (typed + severity-rated), increments Prometheus counters, and lands
in a rolling feed. Prometheus scrapes /metrics; the dashboard polls /security/recent.
This is the first module of the CloudSentinel-AI security-observability vision.
"""

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field, field_validator

from app.backends.base import ChatMessage
from app.config import get_backend, settings
from app.pipeline.auth import require_api_key
from app.pipeline.guardrails import get_guardrails
from app.pipeline.logging_setup import get_logger
from app.pipeline.metrics import (
    REQUEST_LATENCY,
    REQUESTS_BLOCKED_TOTAL,
    REQUESTS_TOTAL,
    SECURITY_EVENTS_TOTAL,
)
from app.pipeline.security_events import feed

app = FastAPI(title="vLLM Inference Stack -- App Layer")

backend = get_backend()
guardrails = get_guardrails()
logger = get_logger()


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[Message] = Field(min_length=1)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user(cls, messages: list[Message]) -> list[Message]:
        if messages[-1].role != "user":
            raise ValueError("the last message must have role 'user'")
        return messages


def _record_security_event(stage: str, reason: str, request_id: str, text: str) -> None:
    """Emit a structured security event: feed + Prometheus counters + log."""
    event = feed.record(stage=stage, reason=reason, request_id=request_id, text=text)
    SECURITY_EVENTS_TOTAL.labels(
        event_type=event.event_type,
        severity=event.severity,
        stage=event.stage,
        action=event.action,
    ).inc()
    REQUESTS_BLOCKED_TOTAL.inc()
    logger.info("security event", extra={"data": {
        "request_id": request_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "stage": event.stage,
        "reason": event.reason,
    }})


# ---- Routes ----

@app.get("/health")
async def health():
    ok = await backend.health()
    return {"status": "ok" if ok else "unavailable", "backend": settings.backend}


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/security/recent")
async def security_recent(limit: int = 50):
    """Recent security events feed (powers the dashboard's recent-attacks panel)."""
    return {"events": feed.recent(limit)}


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(req: ChatRequest):
    request_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    started = time.perf_counter()
    REQUESTS_TOTAL.inc()
    messages = [ChatMessage(role=m.role, content=m.content) for m in req.messages]
    user_text = next((m.content for m in reversed(messages) if m.role == "user"), "")

    # --- input guardrails ---
    gate_in = await guardrails.check_input(messages)
    if not gate_in.allowed:
        _record_security_event("input", gate_in.reason, request_id, user_text)
        REQUEST_LATENCY.observe(time.perf_counter() - started)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Blocked by input guardrail: {gate_in.reason}")

    if req.stream:
        return StreamingResponse(
            _stream_sse(req, messages, request_id, started),
            media_type="text/event-stream",
        )

    result = await backend.generate(
        messages=messages, max_tokens=req.max_tokens, temperature=req.temperature,
    )

    gate_out = await guardrails.check_output(result.content)
    if not gate_out.allowed:
        _record_security_event("output", gate_out.reason, request_id, result.content)
        REQUEST_LATENCY.observe(time.perf_counter() - started)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Blocked by output guardrail: {gate_out.reason}")

    elapsed = time.perf_counter() - started
    REQUEST_LATENCY.observe(elapsed)
    logger.info("request completed", extra={"data": {
        "request_id": request_id, "backend": settings.backend, "stream": False,
        "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens, "latency_ms": round(elapsed * 1000, 1),
        "status": 200,
    }})

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model or settings.model_name,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": result.content},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": result.prompt_tokens,
                  "completion_tokens": result.completion_tokens,
                  "total_tokens": result.total_tokens},
    }


async def _stream_sse(req, messages, request_id, started) -> AsyncIterator[str]:
    created = int(time.time())
    model = req.model or settings.model_name

    def sse(delta, finish=None):
        payload = {"id": request_id, "object": "chat.completion.chunk",
                   "created": created, "model": model,
                   "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        return f"data: {json.dumps(payload)}\n\n"

    yield sse({"role": "assistant"})
    full_text = ""
    async for chunk in backend.stream(messages, max_tokens=req.max_tokens,
                                      temperature=req.temperature):
        full_text += chunk
        yield sse({"content": chunk})

    gate_out = await guardrails.check_output(full_text)
    if not gate_out.allowed:
        _record_security_event("output", gate_out.reason, request_id, full_text)
        yield sse({"content": f"\n[blocked by output guardrail: {gate_out.reason}]"}, finish="stop")
        yield "data: [DONE]\n\n"
        return

    yield sse({}, finish="stop")
    yield "data: [DONE]\n\n"
    REQUEST_LATENCY.observe(time.perf_counter() - started)
    logger.info("request completed", extra={"data": {
        "request_id": request_id, "backend": settings.backend, "stream": True,
        "completion_chars": len(full_text), "status": 200,
    }})
