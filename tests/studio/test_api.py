"""Tests for Studio FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from Studio.api import create_app


@pytest.fixture
def client():
    """Provide a test client for the Studio API with lifespan events."""
    app = create_app(seed_data=False)
    with TestClient(app) as c:
        yield c


def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["healthy"] is True


def test_get_characters_empty(client):
    response = client.get("/characters")
    assert response.status_code == 200
    data = response.json()
    assert data["characters"] == []


def test_create_and_get_character(client):
    # Create a character
    response = client.post("/characters", json={
        "name": "Hero",
        "role": "Protagonist",
        "status": "active",
    })
    assert response.status_code == 200

    # Verify it exists
    response = client.get("/characters")
    data = response.json()
    assert len(data["characters"]) == 1
    assert data["characters"][0]["name"] == "Hero"
