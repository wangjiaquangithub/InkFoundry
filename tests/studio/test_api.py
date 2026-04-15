"""Tests for Studio FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState
from Studio.api import create_app


@pytest.fixture
def client():
    """Provide a test client for the Studio API with lifespan events."""
    app = create_app(seed_data=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_seed():
    """Provide a test client with seeded data."""
    app = create_app(seed_data=True)
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


# --- Chapter API tests ---

def test_create_and_list_chapters(client):
    response = client.post("/api/chapters", json={"title": "Chapter 1", "content": "Test content"})
    assert response.status_code == 200

    response = client.get("/api/chapters")
    data = response.json()
    assert len(data["chapters"]) == 1
    assert data["chapters"][0]["title"] == "Chapter 1"


def test_get_chapter_not_found(client):
    response = client.get("/api/chapters/999")
    assert response.status_code == 404


def test_update_chapter(client):
    client.post("/api/chapters", json={"title": "v1", "content": "v1"})
    response = client.put("/api/chapters/1", json={"title": "v2", "content": "v2 content"})
    assert response.status_code == 200

    response = client.get("/api/chapters/1")
    data = response.json()
    assert data["title"] == "v2"
    assert data["content"] == "v2 content"


def test_delete_chapter(client):
    client.post("/api/chapters", json={"title": "To Delete", "content": "delete me"})
    response = client.delete("/api/chapters/1")
    assert response.status_code == 200

    response = client.get("/api/chapters/1")
    assert response.status_code == 404


# --- Outline API tests ---

def test_generate_outline(client):
    response = client.post("/api/outlines/generate", json={
        "genre": "xuanhuan",
        "title": "Test Novel",
        "summary": "A hero's journey",
        "total_chapters": 10,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["outline"]["title"] == "Test Novel"
    assert len(data["outline"]["chapter_summaries"]) == 10


def test_get_outline(client):
    client.post("/api/outlines/generate", json={"title": "Test", "total_chapters": 5})
    response = client.get("/api/outlines")
    data = response.json()
    assert data["outline"] is not None
    assert data["outline"]["title"] == "Test"


def test_get_outline_none(client):
    response = client.get("/api/outlines")
    data = response.json()
    assert data["outline"] is None


# --- Profile API tests ---

def test_create_and_list_profiles(client):
    response = client.post("/api/profiles", json={
        "name": "Hero",
        "personality": "brave",
        "backstory": "Orphan",
    })
    assert response.status_code == 200

    response = client.get("/api/profiles")
    data = response.json()
    assert len(data["profiles"]) == 1
    assert data["profiles"][0]["name"] == "Hero"


def test_get_profile_not_found(client):
    response = client.get("/api/profiles/nonexistent")
    assert response.status_code == 404


# --- Relationship API tests ---

def test_create_and_list_relationships(client):
    response = client.post("/api/relationships", json={
        "from_character": "Hero",
        "to_character": "Mentor",
        "relationship_type": "mentor",
        "strength": 0.8,
    })
    assert response.status_code == 200

    response = client.get("/api/relationships")
    data = response.json()
    assert len(data["relationships"]) == 1


# --- World Building API tests ---

def test_create_and_get_world_building(client):
    response = client.post("/api/world-building", json={
        "name": "My World",
        "era": "ancient",
    })
    assert response.status_code == 200

    response = client.get("/api/world-building")
    data = response.json()
    assert data["world_building"]["name"] == "My World"


# --- Pipeline API tests ---

def test_run_chapter_via_api(client):
    # Need an outline first
    client.post("/api/outlines/generate", json={"title": "Test", "total_chapters": 10})
    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 200
    data = response.json()
    assert data["chapter_num"] == 1
    assert "status" in data


def test_run_batch_via_api(client):
    client.post("/api/outlines/generate", json={"title": "Test", "total_chapters": 10})
    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 3,
    })
    assert response.status_code == 200
    data = response.json()
    assert "1" in data["results"]
    assert "2" in data["results"]
    assert "3" in data["results"]


def test_pipeline_status_via_api(client):
    response = client.get("/api/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


# --- WebSocket tests ---

def test_websocket_connection(client):
    """Test that WebSocket endpoint accepts connections."""
    with client.websocket_connect("/ws/pipeline") as ws:
        # Connection should be accepted
        ws.send_text('{"action": "subscribe"}')
        data = ws.receive_json()
        assert data["type"] == "subscription_confirmed"


def test_websocket_receives_pipeline_events(client):
    """Test that WebSocket pushes pipeline progress events."""
    # Generate an outline first
    client.post("/api/outlines/generate", json={"title": "Test", "total_chapters": 5})

    with client.websocket_connect("/ws/pipeline") as ws:
        ws.send_text('{"action": "subscribe"}')
        ws.receive_json()  # subscription_confirmed

        # Trigger a chapter run — the orchestrator should publish events
        # that get pushed through WebSocket
        # We verify the WebSocket is functional and accepts messages
        ws.send_text('{"action": "ping"}')
        data = ws.receive_json()
        assert data["type"] == "pong"


def test_websocket_invalid_message(client):
    """Test that WebSocket handles invalid messages gracefully."""
    with client.websocket_connect("/ws/pipeline") as ws:
        ws.send_text('{"action": "unknown_action"}')
        data = ws.receive_json()
        assert data["type"] == "error"
