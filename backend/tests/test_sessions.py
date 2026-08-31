"""Unit tests for Session Domain Models and Memory Persistence."""

import pytest
from core.models.session import Session, MessageRole, ConversationPhase
from core.models.user_profile import UserProfile, ThinkingStyle
from adapters.memory_adapter import InMemoryAdapter


@pytest.mark.asyncio
async def test_session_lifecycle_and_serialization():
    """Test session creation, message appending, and dictionary conversion."""
    session = Session(user_id="user_prod_007", title="GPU Benchmark Comparison")
    session.add_message(MessageRole.USER, "Evaluate H100 vs TPU v5p", "text")
    session.add_message(MessageRole.AGENT, "Let's analyze batch size and latency requirements.", "question")

    session_dict = session.to_dict()
    assert session_dict["user_id"] == "user_prod_007"
    assert session_dict["title"] == "GPU Benchmark Comparison"
    assert len(session_dict["messages"]) == 2

    # Reconstruct from dict
    restored = Session.from_dict(session_dict)
    assert restored.id == session.id
    assert restored.user_id == session.user_id
    assert len(restored.messages) == 2
    assert restored.messages[0].content == "Evaluate H100 vs TPU v5p"


@pytest.mark.asyncio
async def test_in_memory_adapter(in_memory_adapter, sample_session):
    """Test full CRUD operations on InMemoryAdapter."""
    # Save
    await in_memory_adapter.save_session(sample_session)

    # Load
    loaded = await in_memory_adapter.load_session(sample_session.id)
    assert loaded is not None
    assert loaded.id == sample_session.id
    assert len(loaded.messages) == 2

    # List
    sessions = await in_memory_adapter.list_sessions("test_user_001")
    assert len(sessions) == 1
    assert sessions[0]["id"] == sample_session.id

    # Delete
    await in_memory_adapter.delete_session(sample_session.id)
    deleted = await in_memory_adapter.load_session(sample_session.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_user_profile_persistence(in_memory_adapter):
    """Test saving and loading user profiles."""
    profile = UserProfile(user_id="user_researcher_99", thinking_style={"analytical": 85, "speed": 40})
    await in_memory_adapter.save_user_profile(profile)

    loaded_profile = await in_memory_adapter.load_user_profile("user_researcher_99")
    assert loaded_profile is not None
    assert loaded_profile.user_id == "user_researcher_99"
    assert loaded_profile.thinking_style.analytical == 85
    assert loaded_profile.thinking_style.speed == 40
