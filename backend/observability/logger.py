"""Structured JSON logging with trace ID propagation.

Every log entry includes a trace_id for end-to-end request tracing.
This satisfies the observability requirement for architectural discipline.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar

# Context variable for trace ID propagation across async calls
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Get current trace ID or generate a new one."""
    trace_id = current_trace_id.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())[:8]
        current_trace_id.set(trace_id)
    return trace_id


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", get_trace_id()),
        }
        # Include extra fields
        for key in ("event_type", "source", "agent", "duration_ms"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        if record.exc_info and record.exc_info[1]:
            log_data["error"] = str(record.exc_info[1])
        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger("synthmind")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
