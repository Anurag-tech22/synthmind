"""Document domain models — represents processed multimodal inputs.

Handles the structured output from Gemini's multimodal processing
of PDFs, images, URLs, and raw text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DocumentChunk:
    """A semantically meaningful chunk extracted from a document."""
    id: str = ""
    content: str = ""
    chunk_type: str = "text"  # text, table, image_description, heading, list
    page_number: int | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class ProcessedDocument:
    """A document that has been processed by the Ingester agent.

    Represents the structured extraction from any input modality:
    PDF, image, URL, or raw text paste.
    """
    id: str = ""
    source_type: str = "text"  # pdf, image, url, text, csv
    source_name: str = ""      # Original filename or URL
    title: str = ""
    summary: str = ""
    chunks: list[DocumentChunk] = field(default_factory=list)
    raw_text: str = ""
    key_facts: list[str] = field(default_factory=list)
    entities: list[dict[str, str]] = field(default_factory=list)
    # Each entity: {"name": str, "type": str} (person, org, product, date, etc.)
    processed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "title": self.title,
            "summary": self.summary,
            "chunks": [c.to_dict() for c in self.chunks],
            "raw_text": self.raw_text[:5000],  # Limit for storage
            "key_facts": self.key_facts,
            "entities": self.entities,
            "processed_at": self.processed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessedDocument:
        return cls(
            id=data.get("id", ""),
            source_type=data.get("source_type", "text"),
            source_name=data.get("source_name", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            chunks=[
                DocumentChunk(**c) for c in data.get("chunks", [])
            ],
            raw_text=data.get("raw_text", ""),
            key_facts=data.get("key_facts", []),
            entities=data.get("entities", []),
            processed_at=data.get("processed_at", ""),
        )

    @property
    def full_text(self) -> str:
        """Get all text content concatenated."""
        if self.raw_text:
            return self.raw_text
        return "\n\n".join(c.content for c in self.chunks if c.content)
