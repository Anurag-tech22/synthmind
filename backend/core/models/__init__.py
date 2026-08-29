"""Domain models for SynthMind - pure Python, no external dependencies."""

from core.models.session import Session, Message, MessageRole, ConversationPhase
from core.models.synthesis import (
    SynthesisOutput, DecisionMatrix, ComparisonTable,
    ProsCons, SwotAnalysis, KeyInsight, KnowledgeMap, TimelineEntry
)
from core.models.user_profile import UserProfile, ThinkingStyle
from core.models.document import ProcessedDocument, DocumentChunk

__all__ = [
    "Session", "Message", "MessageRole", "ConversationPhase",
    "SynthesisOutput", "DecisionMatrix", "ComparisonTable",
    "ProsCons", "SwotAnalysis", "KeyInsight", "KnowledgeMap", "TimelineEntry",
    "UserProfile", "ThinkingStyle",
    "ProcessedDocument", "DocumentChunk",
]
