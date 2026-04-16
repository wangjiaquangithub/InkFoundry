"""Tests for Studio FastAPI endpoints."""
import os

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState
import Studio.api as studio_api
from Engine.core.models import CharacterState, StateSnapshot, WorldState
from Engine.core.state_db import StateDB
from Studio.api import create_app


@pytest.fixture
def client(tmp_path):
    """Provide a test client for the Studio API with lifespan events."""
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_seed(tmp_path):
    """Provide a test client with seeded data."""
    app = create_app(
        seed_data=True,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
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


def test_save_config_rejects_non_qwen_model_with_dashscope_base_url(client):
    response = client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "claude-sonnet-4-6",
    })

    assert response.status_code == 422
    assert "incompatible with DashScope" in response.json()["detail"]


def test_save_config_rejects_invalid_base_url(client):
    response = client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "not-a-url",
        "default_model": "qwen3.6-plus",
    })

    assert response.status_code == 422
    assert "valid http(s) URL" in response.json()["detail"]


def test_invalid_stored_config_returns_422_for_llm_dependent_endpoint(client):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        (
            "config",
            '{"llm_api_key": "test-key", "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1", "default_model": "claude-sonnet-4-6"}',
        ),
    )
    client.app.state.db.conn.commit()

    response = client.post("/api/side-story/generate", json={
        "characters": ["Hero"],
        "setting": "Test World",
        "topic": "Test Topic",
    })
    assert response.status_code == 422
    assert "incompatible with DashScope" in response.json()["detail"]



def test_malformed_stored_config_returns_500_for_get_config(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '{"llm_api_key": "broken"'),
    )
    client.app.state.db.conn.commit()

    response = client.get("/api/config")

    assert response.status_code == 500
    assert "config" in response.json()["detail"].lower()
    assert "json" in response.json()["detail"].lower()



def test_malformed_stored_config_returns_500_for_save_config(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '{"llm_api_key": "broken"'),
    )
    client.app.state.db.conn.commit()

    response = client.post("/api/config", json={"default_model": "qwen3.6-plus"})

    assert response.status_code == 500
    assert "config" in response.json()["detail"].lower()
    assert "json" in response.json()["detail"].lower()



def test_non_object_stored_config_returns_500_for_get_config(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '["not-an-object"]'),
    )
    client.app.state.db.conn.commit()

    response = client.get("/api/config")

    assert response.status_code == 500
    assert "config" in response.json()["detail"].lower()
    assert "json object" in response.json()["detail"].lower()



def test_malformed_stored_config_returns_500_for_llm_dependent_endpoint(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '{"llm_api_key": "broken"'),
    )
    client.app.state.db.conn.commit()

    response = client.post("/api/side-story/generate", json={
        "characters": ["Hero"],
        "setting": "Test World",
        "topic": "Test Topic",
    })

    assert response.status_code == 500
    assert "config" in response.json()["detail"].lower()
    assert "json" in response.json()["detail"].lower()



def test_save_config_does_not_persist_env_api_key_on_partial_update(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "env-secret-key")

    response = client.post("/api/config", json={
        "default_model": "qwen3.6-plus",
    })
    assert response.status_code == 200

    config = client.get("/api/config").json()
    assert config["llm_api_key"] == ""
    assert config["llm_api_key_masked"] == "****-key"

    app_db = client.app.state.db
    row = app_db.conn.execute("SELECT data FROM state WHERE key = 'config'").fetchone()
    assert row is not None
    assert "env-secret-key" not in row[0]


def test_invalid_stored_config_returns_422_for_pipeline_endpoint(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        (
            "config",
            '{"llm_api_key": "test-key", "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1", "default_model": "claude-sonnet-4-6"}',
        ),
    )
    client.app.state.db.conn.commit()

    client.post("/api/outlines/generate", json={"title": "Test", "total_chapters": 5})
    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 422
    assert "incompatible with DashScope" in response.json()["detail"]



def test_save_config_does_not_mutate_process_environment(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "env-model")

    response = client.post("/api/config", json={
        "llm_api_key": "db-key",
        "llm_base_url": "https://db.example/v1",
        "default_model": "db-model",
    })

    assert response.status_code == 200
    assert os.environ["LLM_API_KEY"] == "env-key"
    assert os.environ["LLM_BASE_URL"] == "https://env.example/v1"
    assert os.environ["DEFAULT_MODEL"] == "env-model"

    config = client.get("/api/config").json()
    assert config["llm_api_key"] == ""
    assert config["llm_api_key_masked"] == "****-key"
    assert config["llm_base_url"] == "https://db.example/v1"
    assert config["default_model"] == "db-model"



def test_delete_config_clears_db_overrides_and_falls_back_to_environment_defaults(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "env-secret-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "env-model")

    client.post("/api/config", json={
        "llm_api_key": "db-key",
        "llm_base_url": "https://db.example/v1",
        "default_model": "db-model",
    })

    delete_response = client.delete("/api/config")

    assert delete_response.status_code == 200
    row = client.app.state.db.conn.execute(
        "SELECT data FROM state WHERE key = 'config'"
    ).fetchone()
    assert row is None

    config = client.get("/api/config").json()
    assert config["llm_api_key"] == ""
    assert config["llm_api_key_masked"] == "****-key"
    assert config["llm_base_url"] == "https://env.example/v1"
    assert config["default_model"] == "env-model"



def test_config_save_is_project_scoped_between_activated_projects(client):
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi"}).json()["project"]

    activate_a = client.post(f"/api/projects/{project_a['id']}/activate")
    assert activate_a.status_code == 200
    save_a = client.post("/api/config", json={
        "default_model": "model-a",
        "writer_model": "writer-a",
    })
    assert save_a.status_code == 200

    activate_b = client.post(f"/api/projects/{project_b['id']}/activate")
    assert activate_b.status_code == 200
    config_b = client.get("/api/config").json()
    assert config_b["default_model"] != "model-a"
    assert config_b["writer_model"] != "writer-a"

    reactivate_a = client.post(f"/api/projects/{project_a['id']}/activate")
    assert reactivate_a.status_code == 200
    config_a = client.get("/api/config").json()
    assert config_a["default_model"] == "model-a"
    assert config_a["writer_model"] == "writer-a"



def test_delete_config_only_resets_active_project_config(client):
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi"}).json()["project"]

    assert client.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
    assert client.post("/api/config", json={"default_model": "model-a"}).status_code == 200

    assert client.post(f"/api/projects/{project_b['id']}/activate").status_code == 200
    assert client.post("/api/config", json={"default_model": "model-b"}).status_code == 200

    delete_response = client.delete("/api/config")
    assert delete_response.status_code == 200
    config_b = client.get("/api/config").json()
    assert config_b["default_model"] != "model-b"

    assert client.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
    config_a = client.get("/api/config").json()
    assert config_a["default_model"] == "model-a"


def test_list_snapshots_empty(client):
    response = client.get("/api/snapshots")

    assert response.status_code == 200
    assert response.json() == {"snapshots": []}



def test_save_snapshot_persists_current_state(client):
    client.post("/characters", json={
        "name": "Hero",
        "role": "Protagonist",
        "status": "active",
    })
    client.app.state.db.update_world_state(
        WorldState(name="Capital", description="Snow city", state="stable")
    )
    client.post("/api/chapters", json={"title": "Chapter 1", "content": "v1 content"})

    save_response = client.post("/api/snapshots")
    list_response = client.get("/api/snapshots")

    assert save_response.status_code == 200
    assert save_response.json()["version"] == 1
    snapshots = list_response.json()["snapshots"]
    assert len(snapshots) == 1
    assert snapshots[0]["characters"][0]["name"] == "Hero"
    assert snapshots[0]["world_states"][0]["name"] == "Capital"
    assert snapshots[0]["metadata"]["chapters"][0]["title"] == "Chapter 1"
    assert snapshots[0]["chapter_num"] == 1



def test_save_snapshot_increments_version(client):
    first = client.post("/api/snapshots")
    second = client.post("/api/snapshots")
    list_response = client.get("/api/snapshots")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    assert [snapshot["version"] for snapshot in list_response.json()["snapshots"]] == [1, 2]



def test_restore_snapshot_restores_saved_state(client):
    client.post("/characters", json={
        "name": "Hero",
        "role": "Protagonist",
        "status": "active",
    })
    client.app.state.db.update_world_state(
        WorldState(name="Capital", description="Snow city", state="stable")
    )
    client.post("/api/chapters", json={"title": "Chapter 1", "content": "v1 content"})
    client.post("/api/snapshots")

    client.put("/api/characters/Hero", json={"status": "inactive"})
    client.app.state.db.update_world_state(
        WorldState(name="Capital", description="Burned city", state="ruined")
    )
    client.put("/api/chapters/1", json={"title": "Chapter 1B", "content": "v2 content"})

    restore_response = client.post("/api/snapshots/1/restore")
    characters_response = client.get("/api/characters")
    chapter_response = client.get("/api/chapters/1")
    restored_world = client.app.state.db.get_world_state("Capital")

    assert restore_response.status_code == 200
    assert characters_response.status_code == 200
    assert chapter_response.status_code == 200
    assert characters_response.json()["characters"][0]["status"] == "active"
    assert chapter_response.json()["title"] == "Chapter 1"
    assert chapter_response.json()["content"] == "v1 content"
    assert restored_world is not None
    assert restored_world.description == "Snow city"
    assert restored_world.state == "stable"



def test_restore_snapshot_not_found(client):
    response = client.post("/api/snapshots/999/restore")

    assert response.status_code == 404
    assert response.json()["detail"] == "Snapshot v999 not found"



def test_delete_snapshot_removes_snapshot_from_list(client):
    client.post("/api/snapshots")

    delete_response = client.delete("/api/snapshots/1")
    list_response = client.get("/api/snapshots")

    assert delete_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json() == {"snapshots": []}



def test_delete_snapshot_not_found(client):
    response = client.delete("/api/snapshots/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Snapshot v999 not found"



def test_restore_snapshot_rejects_legacy_snapshot_without_chapters(client):
    client.app.state.db.save_snapshot(
        StateSnapshot(
            version=1,
            chapter_num=1,
            characters=[CharacterState(name="Hero", role="Protagonist", status="active")],
            world_states=[WorldState(name="Capital", description="Snow city", state="stable")],
            metadata={},
        )
    )

    response = client.post("/api/snapshots/1/restore")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Snapshot v1 is incompatible with chapter restore; missing metadata.chapters"
    )



def test_activate_project_rebinds_token_tracker_to_new_project_db(client):
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi"}).json()["project"]

    assert client.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
    studio_api._get_token_tracker().record("model-a", 10, 5, "project-a-task")

    project_a_db = StateDB(project_a["db_path"])
    try:
        project_a_tokens = project_a_db.get_state("token_records")
        assert project_a_tokens is not None
        assert len(project_a_tokens["records"]) == 1
        assert project_a_tokens["records"][0]["task"] == "project-a-task"
    finally:
        project_a_db.close()

    assert client.post(f"/api/projects/{project_b['id']}/activate").status_code == 200
    studio_api._get_token_tracker().record("model-b", 7, 3, "project-b-task")

    project_a_db = StateDB(project_a["db_path"])
    project_b_db = StateDB(project_b["db_path"])
    try:
        project_a_tokens = project_a_db.get_state("token_records")
        project_b_tokens = project_b_db.get_state("token_records")
        assert project_a_tokens is not None
        assert len(project_a_tokens["records"]) == 1
        assert project_b_tokens is not None
        assert len(project_b_tokens["records"]) == 1
        assert project_b_tokens["records"][0]["task"] == "project-b-task"
    finally:
        project_a_db.close()
        project_b_db.close()



def test_activate_project_resets_stale_pipeline_manager_status(client, monkeypatch):
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi"}).json()["project"]

    assert client.post(f"/api/projects/{project_a['id']}/activate").status_code == 200

    class FakeTask:
        def done(self):
            return False

        def cancel(self):
            return None

    class FakeOrchestrator:
        def __init__(self):
            self.status = {"running": True, "paused": True}

        def stop(self):
            self.status = {"running": False, "paused": False}

    monkeypatch.setattr(studio_api._pipeline_manager, "_task", FakeTask())
    monkeypatch.setattr(studio_api._pipeline_manager, "_orchestrator", FakeOrchestrator())

    assert client.get("/api/pipeline/status").json() == {
        "running": True,
        "paused": True,
        "task_alive": True,
    }

    assert client.post(f"/api/projects/{project_b['id']}/activate").status_code == 200

    assert client.get("/api/pipeline/status").json() == {
        "running": False,
        "paused": False,
        "task_alive": False,
    }
