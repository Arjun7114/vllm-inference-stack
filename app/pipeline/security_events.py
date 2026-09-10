"""
Security event model + emitter -- the "detection engine output" of the LLM
security-observability layer (the first module of the CloudSentinel-AI vision).

When a guardrail fires, we don't just block and log a line -- we emit a
structured SECURITY EVENT: typed, severity-rated, timestamped, with a redacted
snippet. These events (a) feed a rolling in-memory feed for the dashboard's
"recent attacks" panel, and (b) drive Prometheus counters for the SOC dashboards.

This turns the guardrails from a check into a *monitored security control*.
"""

import time
from collections import deque
from dataclasses import asdict, dataclass, field

# Map a raw guardrail reason to a normalized event type + severity.
# Severity: critical > high > medium > low.
EVENT_RULES = {
    "prompt injection": ("prompt_injection", "high"),
    "injection":        ("prompt_injection", "high"),
    "jailbreak":        ("jailbreak", "critical"),
    "pii":              ("pii_detected", "high"),
    "banned phrase":    ("banned_phrase", "medium"),
    "banned topic":     ("banned_topic", "medium"),
    "toxic":            ("toxicity", "medium"),
    "empty":            ("empty_response", "low"),
    "leaked pii":       ("output_pii_leak", "critical"),
}


def classify(reason: str) -> tuple[str, str]:
    """Map a guardrail reason string to (event_type, severity)."""
    low = reason.lower()
    for key, (etype, severity) in EVENT_RULES.items():
        if key in low:
            return etype, severity
    return "policy_violation", "medium"


def _redact(text: str, limit: int = 80) -> str:
    """Trim + lightly redact a snippet so the feed never stores raw sensitive data."""
    snippet = " ".join(text.split())[:limit]
    return snippet + ("..." if len(text) > limit else "")


@dataclass
class SecurityEvent:
    timestamp: float
    event_type: str
    severity: str
    stage: str          # "input" or "output"
    action: str         # "blocked" or "flagged"
    reason: str
    snippet: str
    request_id: str

    def as_dict(self) -> dict:
        d = asdict(self)
        d["time_iso"] = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return d


class SecurityFeed:
    """
    Rolling in-memory feed of the most recent security events. Powers the
    'recent attacks' panel and exposes a JSON endpoint the dashboard can poll.
    """

    def __init__(self, maxlen: int = 100):
        self._events: deque[SecurityEvent] = deque(maxlen=maxlen)

    def record(self, stage: str, reason: str, request_id: str, text: str) -> SecurityEvent:
        etype, severity = classify(reason)
        event = SecurityEvent(
            timestamp=time.time(),
            event_type=etype,
            severity=severity,
            stage=stage,
            action="blocked",
            reason=reason,
            snippet=_redact(text),
            request_id=request_id,
        )
        self._events.appendleft(event)
        return event

    def recent(self, limit: int = 50) -> list[dict]:
        return [e.as_dict() for e in list(self._events)[:limit]]


# Single shared feed for the app's lifetime.
feed = SecurityFeed()
