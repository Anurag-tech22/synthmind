"""Integration tests for FastAPI REST and Calculation endpoints."""

import pytest
from fastapi.testclient import TestClient
from main import app, memory
from core.models.session import Session, MessageRole, ConversationPhase


@pytest.fixture
def client():
    """Fixture providing FastAPI TestClient."""
    return TestClient(app)


def test_health_check(client):
    """Test /api/health endpoint returns healthy status and metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "synthmind"
    assert "framework" in data


def test_recalculate_endpoint(client, sample_criteria_options):
    """Test /api/recalculate recalculates MCDA weights via HTTP POST."""
    criteria, options = sample_criteria_options
    response = client.post(
        "/api/recalculate",
        json={"criteria": criteria, "options": options},
    )
    assert response.status_code == 200
    data = response.json()
    assert "options" in data
    assert len(data["options"]) == 2
    assert data["options"][0]["name"] == "Cloud Run"
    assert data["options"][0]["total_weighted"] == 8.90


@pytest.mark.asyncio
async def test_export_endpoint(client, sample_session):
    """Test /api/export generates executive markdown summary."""
    # Pre-save session to memory
    await memory.save_session(sample_session)

    response = client.post(
        "/api/export",
        json={"session_id": sample_session.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "markdown" in data
    assert sample_session.id in data["markdown"]
    assert "Executive Research Brief" in data["markdown"]


def test_events_endpoint(client):
    """Test /api/events observability endpoint returns event log."""
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
