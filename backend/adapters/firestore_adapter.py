"""Google Cloud Firestore Adapter — Cloud Infrastructure Memory Persistence.

Implements MemoryPort using Google Cloud Firestore / Firebase Firestore (NoSQL).
Provides persistent session state, multi-agent trace logs, and user profile
history backed by Google Cloud infrastructure.
"""

from __future__ import annotations

import logging
from typing import Any

from core.interfaces.memory_port import MemoryPort
from core.models.session import Session
from core.models.user_profile import UserProfile

logger = logging.getLogger("synthmind.firestore")


class FirestoreMemoryAdapter(MemoryPort):
    """Google Cloud Firestore implementation of MemoryPort.

    Persists sessions, messages, synthesis artifacts, and user profiles
    to Google Cloud Firestore with automatic collection indexing.
    """

    def __init__(self, project_id: str = "", credentials_path: str = "") -> None:
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._db = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google Cloud Firestore client."""
        try:
            from google.cloud import firestore

            if self.credentials_path:
                self._db = firestore.Client.from_service_account_json(
                    self.credentials_path,
                    project=self.project_id or None,
                )
            elif self.project_id:
                self._db = firestore.Client(project=self.project_id)
            else:
                self._db = firestore.Client()

            logger.info("Connected to Google Cloud Firestore (Project: %s)", self.project_id or "default")
        except Exception as exc:
            logger.warning("Firestore client init failed (will fallback if needed): %s", str(exc))
            self._db = None

    @property
    def is_connected(self) -> bool:
        """Check if Firestore client is initialized and reachable."""
        return self._db is not None

    async def save_session(self, session: Session) -> None:
        """Save or update a session in the 'synthmind_sessions' collection."""
        if not self._db:
            return
        try:
            doc_ref = self._db.collection("synthmind_sessions").document(session.id)
            doc_ref.set(session.to_dict())
            logger.debug("Session %s saved to Firestore", session.id)
        except Exception as exc:
            logger.error("Failed to save session to Firestore: %s", str(exc))

    async def load_session(self, session_id: str) -> Session | None:
        """Load a session by ID from Firestore."""
        if not self._db:
            return None
        try:
            doc_ref = self._db.collection("synthmind_sessions").document(session_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return Session.from_dict(doc.to_dict())
        except Exception as exc:
            logger.error("Failed to load session from Firestore: %s", str(exc))
            return None

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Query sessions for a specific user ordered by last updated timestamp."""
        if not self._db:
            return []
        try:
            query = (
                self._db.collection("synthmind_sessions")
                .where("user_id", "==", user_id)
                .order_by("updated_at", direction="DESCENDING")
                .limit(limit)
            )
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                results.append({
                    "id": data.get("id"),
                    "title": data.get("title", "Untitled Session"),
                    "phase": data.get("phase", "onboarding"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                })
            return results
        except Exception as exc:
            logger.error("Failed to list sessions from Firestore: %s", str(exc))
            return []

    async def save_user_profile(self, profile: UserProfile) -> None:
        """Save a user profile in the 'synthmind_users' collection."""
        if not self._db:
            return
        try:
            doc_ref = self._db.collection("synthmind_users").document(profile.user_id)
            doc_ref.set(profile.to_dict())
        except Exception as exc:
            logger.error("Failed to save user profile to Firestore: %s", str(exc))

    async def load_user_profile(self, user_id: str) -> UserProfile | None:
        """Load a user profile by ID from Firestore."""
        if not self._db:
            return None
        try:
            doc_ref = self._db.collection("synthmind_users").document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return UserProfile.from_dict(doc.to_dict())
        except Exception as exc:
            logger.error("Failed to load user profile from Firestore: %s", str(exc))
            return None

    async def delete_session(self, session_id: str) -> None:
        """Delete a session document from Firestore."""
        if not self._db:
            return
        try:
            self._db.collection("synthmind_sessions").document(session_id).delete()
            logger.info("Session %s deleted from Firestore", session_id)
        except Exception as exc:
            logger.error("Failed to delete session from Firestore: %s", str(exc))
