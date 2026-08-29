"""Session domain models — tracks conversation state and history.

The Session is the central state container for a research workflow.
It moves through defined phases as the user and agents collaborate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Who sent the message."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationPhase(str, Enum):
    """State machine phases for the research workflow.

    Flow: ONBOARDING → CLARIFICATION → INGESTION → SYNTHESIS → FEEDBACK → (loop back to CLARIFICATION)
    """
    ONBOARDING = "onboarding"
    CLARIFICATION = "clarification"
    INGESTION = "ingestion"
    SYNTHESIS = "synthesis"
    FEEDBACK = "feedback"
    COMPLETE = "complete"


@dataclass
class Message:
    """A single message in the conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    message_type: str = "text"  # text, question, insight, synthesis, alert
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class Session:
    """A research session — the core state container.

    Tracks conversation history, current phase, ingested data,
    synthesis outputs, and user feedback across the research workflow.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "anonymous"
    title: str = "New Research Session"
    phase: ConversationPhase = ConversationPhase.ONBOARDING
    messages: list[Message] = field(default_factory=list)
    # Structured understanding from clarification
    research_context: dict[str, Any] = field(default_factory=dict)
    # Ingested and processed data
    ingested_data: list[dict[str, Any]] = field(default_factory=list)
    # Synthesis outputs (decision matrices, comparisons, etc.)
    synthesis_outputs: list[dict[str, Any]] = field(default_factory=list)
    # User feedback history
    feedback: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_message(self, role: MessageRole, content: str, message_type: str = "text", metadata: dict | None = None) -> Message:
        """Add a message to the conversation history."""
        msg = Message(
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return msg

    def advance_phase(self, next_phase: ConversationPhase) -> None:
        """Transition to the next conversation phase."""
        self.phase = next_phase
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize session for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "phase": self.phase.value,
            "messages": [m.to_dict() for m in self.messages],
            "research_context": self.research_context,
            "ingested_data": self.ingested_data,
            "synthesis_outputs": self.synthesis_outputs,
            "feedback": self.feedback,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize session from storage."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", "anonymous"),
            title=data.get("title", "New Research Session"),
            phase=ConversationPhase(data.get("phase", "onboarding")),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            research_context=data.get("research_context", {}),
            ingested_data=data.get("ingested_data", []),
            synthesis_outputs=data.get("synthesis_outputs", []),
            feedback=data.get("feedback", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
