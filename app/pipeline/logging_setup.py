"""
Structured logging for the app layer.

Emits one JSON record per request with fields a log pipeline (or anomaly
detector) can parse: request id, backend, token counts, latency, status. JSON
lines are what observability tooling consumes downstream — this is the seam that
leads into the Prometheus/Grafana phase.
"""

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Merge any structured fields attached via `extra={"data": {...}}`.
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            payload.update(data)
        return json.dumps(payload)


def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
