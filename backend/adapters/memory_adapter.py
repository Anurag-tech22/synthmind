"""In-Memory adapter — implements MemoryPort without external dependencies.

Used when Firestore is not configured. Perfect for local development
and demo purposes. Data persists only during the server process.
"""

from __future__ import annotations

from typing import Any

from core.interfaces.memory_port import MemoryPort
from core.models.session import Session
from core.models.user_profile import UserProfile


class InMemoryAdapter(MemoryPort):
    """In-memory implementation of the MemoryPort.

    Stores all data in dictionaries. Fast, no dependencies, no cost.
    Data is lost when the process restarts.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    async def save_session(self, session: Session) -> None:
        """Save session to in-memory store."""
        self._sessions[session.id] = session.to_dict()

    async def load_session(self, session_id: str) -> Session | None:
        """Load session from in-memory store."""
        data = self._sessions.get(session_id)
        if data is None:
            return None
        return Session.from_dict(data)

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List sessions for a user."""
        user_sessions = [
            {
                "id": s["id"],
                "title": s["title"],
                "phase": s["phase"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
                "message_count": len(s.get("messages", [])),
            }
            for s in self._sessions.values()
            if s.get("user_id") == user_id
        ]
        user_sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return user_sessions[:limit]

    async def save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile to in-memory store."""
        self._profiles[profile.user_id] = profile.to_dict()

    async def load_user_profile(self, user_id: str) -> UserProfile | None:
        """Load user profile from in-memory store."""
        data = self._profiles.get(user_id)
        if data is None:
            return None
        return UserProfile.from_dict(data)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session from in-memory store."""
        self._sessions.pop(session_id, None)
