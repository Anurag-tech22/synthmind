"""Event system for loose coupling between components.

Every agent action emits typed events through the EventBus.
This enables observability, audit trails, and decoupled reactions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("synthmind.events")


@dataclass
class Event:
    """A typed event emitted by an agent or system component."""
    event_type: str
    source: str          # Which agent/component emitted this
    data: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


# Standard event types
class EventTypes:
    """Constants for all event types in the system."""
    # Session events
    SESSION_CREATED = "session.created"
    SESSION_PHASE_CHANGED = "session.phase_changed"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_ERROR = "agent.error"

    # Clarification events
    QUESTION_ASKED = "clarification.question_asked"
    CONTEXT_UPDATED = "clarification.context_updated"

    # Ingestion events
    DOCUMENT_UPLOADED = "ingestion.document_uploaded"
    DOCUMENT_PROCESSED = "ingestion.document_processed"
    DOCUMENT_ERROR = "ingestion.document_error"

    # Synthesis events
    SYNTHESIS_STARTED = "synthesis.started"
    SYNTHESIS_COMPLETED = "synthesis.completed"
    SYNTHESIS_OUTPUT_CREATED = "synthesis.output_created"

    # Feedback events
    FEEDBACK_RECEIVED = "feedback.received"
    STYLE_UPDATED = "style.updated"


class EventBus:
    """Simple in-process event bus for decoupled communication.

    Supports synchronous event dispatch with multiple listeners.
    All events are also logged for observability.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Event], None]]] = {}
        self._event_log: list[Event] = []

    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Register a listener for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event: Event) -> None:
        """Emit an event to all registered listeners."""
        self._event_log.append(event)
        logger.info(
            "Event emitted",
            extra={
                "event_type": event.event_type,
                "source": event.source,
                "trace_id": event.trace_id,
            },
        )
        for callback in self._listeners.get(event.event_type, []):
            try:
                callback(event)
            except Exception as exc:
                logger.error(
                    "Event handler error: %s",
                    str(exc),
                    extra={"event_type": event.event_type},
                )

    def get_event_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent events for observability dashboard."""
        return [e.to_dict() for e in self._event_log[-limit:]]


# Global event bus instance
event_bus = EventBus()
