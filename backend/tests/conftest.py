"""Pytest configuration and shared fixtures for SynthMind backend test suite."""

import os
import sys
import pytest

# Add backend directory to sys.path for test discovery
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.models.session import Session, MessageRole, ConversationPhase
from adapters.memory_adapter import InMemoryAdapter


@pytest.fixture
def in_memory_adapter():
    """Fixture providing an in-memory session persistence adapter."""
    return InMemoryAdapter()


@pytest.fixture
def sample_session():
    """Fixture providing a initialized sample research session."""
    session = Session(user_id="test_user_001")
    session.add_message(MessageRole.USER, "I want to compare Cloud Run vs Kubernetes for my startup.", "text")
    session.add_message(MessageRole.AGENT, "Let's explore your traffic profile and team size.", "question")
    return session


@pytest.fixture
def sample_criteria_options():
    """Fixture providing standardized MCDA criteria and options for quantitative testing."""
    criteria = [
        {"name": "Cost", "weight": 40},
        {"name": "Performance", "weight": 35},
        {"name": "Ease of Ops", "weight": 25},
    ]
    options = [
        {
            "name": "Cloud Run",
            "scores": {"Cost": 9, "Performance": 8, "Ease of Ops": 10},
        },
        {
            "name": "GKE Standard",
            "scores": {"Cost": 6, "Performance": 10, "Ease of Ops": 5},
        },
    ]
    return criteria, options
