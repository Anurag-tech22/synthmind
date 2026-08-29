"""Port interfaces — abstract boundaries for external services.

These define the contracts that adapters must implement.
The domain core depends ONLY on these interfaces, never on concrete implementations.
This is the key to the hexagonal architecture pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.models.session import Session
from core.models.user_profile import UserProfile


class MemoryPort(ABC):
    """Abstract interface for persistent storage (sessions, profiles).

    Implementations: FirestoreAdapter, InMemoryAdapter (for testing).
    """

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Persist a session to storage."""
        ...

    @abstractmethod
    async def load_session(self, session_id: str) -> Session | None:
        """Load a session from storage by ID."""
        ...

    @abstractmethod
    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions for a user (metadata only)."""
        ...

    @abstractmethod
    async def save_user_profile(self, profile: UserProfile) -> None:
        """Persist a user profile."""
        ...

    @abstractmethod
    async def load_user_profile(self, user_id: str) -> UserProfile | None:
        """Load a user profile by ID."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a session from storage."""
        ...
