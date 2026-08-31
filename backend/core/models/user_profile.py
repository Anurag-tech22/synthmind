"""User profile domain models — tracks thinking style and preferences.

The Adapter agent uses these to learn HOW the user thinks
and adjust communication and synthesis format accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ThinkingStyle:
    """Multi-dimensional representation of a user's thinking style.

    Each dimension is scored 0-100. The Adapter agent updates these
    based on observed interaction patterns and explicit feedback.
    """
    analytical: int = 50      # 0=intuitive, 100=highly analytical
    detail_oriented: int = 50  # 0=big-picture, 100=detail-focused
    visual: int = 50          # 0=textual, 100=highly visual
    structured: int = 50      # 0=freeform, 100=highly structured
    risk_aware: int = 50      # 0=risk-tolerant, 100=risk-averse
    speed: int = 50           # 0=thorough/slow, 100=quick decisions

    def to_dict(self) -> dict[str, int]:
        return {
            "analytical": self.analytical,
            "detail_oriented": self.detail_oriented,
            "visual": self.visual,
            "structured": self.structured,
            "risk_aware": self.risk_aware,
            "speed": self.speed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | ThinkingStyle) -> ThinkingStyle:
        if isinstance(data, ThinkingStyle):
            return data
        if not isinstance(data, dict):
            return cls()
        return cls(**{k: data.get(k, 50) for k in cls.__dataclass_fields__ if k in data or hasattr(cls, k)})

    def dominant_traits(self) -> list[str]:
        """Return the user's strongest thinking traits (score > 65)."""
        traits = []
        if self.analytical > 65:
            traits.append("analytical")
        if self.detail_oriented > 65:
            traits.append("detail-oriented")
        if self.visual > 65:
            traits.append("visual")
        if self.structured > 65:
            traits.append("structured")
        if self.risk_aware > 65:
            traits.append("risk-aware")
        if self.speed > 65:
            traits.append("quick-decision")
        return traits or ["balanced"]


@dataclass
class UserProfile:
    """Persistent user profile stored in Firestore for cross-session learning."""
    user_id: str = "anonymous"
    display_name: str = "Researcher"
    thinking_style: ThinkingStyle = field(default_factory=ThinkingStyle)
    preferred_output_formats: list[str] = field(
        default_factory=lambda: ["decision_matrix", "comparison_table", "key_insights"]
    )
    feedback_history: list[dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0
    topics_researched: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if isinstance(self.thinking_style, dict):
            self.thinking_style = ThinkingStyle.from_dict(self.thinking_style)

    def to_dict(self) -> dict[str, Any]:
        style_dict = (
            self.thinking_style.to_dict()
            if hasattr(self.thinking_style, "to_dict")
            else dict(self.thinking_style)
        )
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "thinking_style": style_dict,
            "preferred_output_formats": self.preferred_output_formats,
            "feedback_history": self.feedback_history[-50:],
            "total_sessions": self.total_sessions,
            "topics_researched": self.topics_researched[-20:],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(
            user_id=data.get("user_id", "anonymous"),
            display_name=data.get("display_name", "Researcher"),
            thinking_style=ThinkingStyle.from_dict(data.get("thinking_style", {})),
            preferred_output_formats=data.get("preferred_output_formats", []),
            feedback_history=data.get("feedback_history", []),
            total_sessions=data.get("total_sessions", 0),
            topics_researched=data.get("topics_researched", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
