"""Unit tests for Conversation State Machine & Phase Transitions."""

import pytest
from core.models.session import Session, MessageRole, ConversationPhase
from main import _determine_phase_transition, _classify_message_type


def test_initial_onboarding_transition():
    """Test session transitions from ONBOARDING to CLARIFICATION after initial prompt."""
    session = Session(user_id="user_123")
    assert session.phase == ConversationPhase.ONBOARDING

    session.add_message(MessageRole.USER, "Compare databases for time series data", "text")
    new_phase = _determine_phase_transition(session, "Let's explore your ingestion rate.", "Compare databases")
    assert new_phase == ConversationPhase.CLARIFICATION


def test_clarification_to_ingestion_transition():
    """Test transition from CLARIFICATION to INGESTION once enough context is gathered."""
    session = Session(user_id="user_123")
    session.phase = ConversationPhase.CLARIFICATION
    for i in range(5):
        session.add_message(MessageRole.USER, f"Context detail {i}", "text")
        session.add_message(MessageRole.AGENT, f"Question {i}", "question")

    agent_response = "I understand your requirements completely. Please share any data or benchmarks you have."
    new_phase = _determine_phase_transition(session, agent_response, "Here is our traffic estimate.")
    assert new_phase == ConversationPhase.INGESTION


def test_ingestion_to_synthesis_transition():
    """Test transition to SYNTHESIS when user requests decision matrix or synthesis."""
    session = Session(user_id="user_123")
    session.phase = ConversationPhase.INGESTION
    session.add_message(MessageRole.USER, "Synthesize our options and build a decision matrix now", "text")

    new_phase = _determine_phase_transition(session, "Generating your matrix...", "Synthesize now")
    assert new_phase == ConversationPhase.SYNTHESIS


def test_synthesis_to_feedback_transition():
    """Test transition from SYNTHESIS to FEEDBACK when structured JSON is generated."""
    session = Session(user_id="user_123")
    session.phase = ConversationPhase.SYNTHESIS
    agent_response = "Here is your decision matrix:\n```json\n{\"type\": \"decision_matrix\"}\n```"

    new_phase = _determine_phase_transition(session, agent_response, "Show me the results")
    assert new_phase == ConversationPhase.FEEDBACK


def test_classify_message_type():
    """Test classification of agent messages for UI styling."""
    assert _classify_message_type("What is your expected RPS?", ConversationPhase.CLARIFICATION) == "question"
    assert _classify_message_type("⚠️ Warning: Higher egress cost detected", ConversationPhase.CLARIFICATION) == "alert"
    assert _classify_message_type("💡 Key Insight: Serverless saves 40%", ConversationPhase.INGESTION) == "insight"
    assert _classify_message_type("Here is the breakdown", ConversationPhase.SYNTHESIS) == "synthesis"
