"""Configuration management using environment variables.

Centralized configuration — no magic numbers, no hardcoded values.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Gemini API (AI Studio — FREE)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # Firebase/Firestore
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"])

    # Feature flags
    enable_firestore: bool = False
    enable_voice: bool = True
    enable_file_upload: bool = True
    enable_search_grounding: bool = True
    max_file_size_mb: int = 10
    max_messages_per_session: int = 200

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000")
        cors_list = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", ""),
            firebase_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            cors_origins=cors_list,
            enable_firestore=os.getenv("ENABLE_FIRESTORE", "false").lower() == "true",
            enable_voice=os.getenv("ENABLE_VOICE", "true").lower() == "true",
            enable_file_upload=os.getenv("ENABLE_FILE_UPLOAD", "true").lower() == "true",
            enable_search_grounding=os.getenv("ENABLE_SEARCH_GROUNDING", "true").lower() == "true",
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "10")),
        )


# Global settings instance
settings = Settings.from_env()
