"""
Prometheus metrics for the LLM security-observability layer.

Exposes counters that let the SOC dashboards compute attack volume, attack-type
breakdown, severity distribution, and block rate. Incremented from the guardrails
path in main.py; scraped by Prometheus at /metrics.
"""

from prometheus_client import Counter, Histogram

# Every request that reaches the app (denominator for block rate).
REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total chat requests received",
)

# Security events, labelled so the dashboard can break them down.
SECURITY_EVENTS_TOTAL = Counter(
    "llm_security_events_total",
    "Total security events (guardrail hits)",
    ["event_type", "severity", "stage", "action"],
)

# Requests blocked (numerator for block rate).
REQUESTS_BLOCKED_TOTAL = Counter(
    "llm_requests_blocked_total",
    "Total requests blocked by guardrails",
)

# End-to-end app-layer latency (perf dashboard).
REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "App-layer request latency in seconds",
)
