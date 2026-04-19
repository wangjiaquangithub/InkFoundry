"""Tests for Studio FastAPI endpoints."""
import logging
import os
import threading

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketState
import Studio.api as studio_api
from Engine.core.models import CharacterState, StateSnapshot, WorldState
from Engine.core.state_db import StateDB
from Studio.api import create_app


ACTIVE_PROJECT_COOKIE = "inkfoundry_active_project_id"


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


@pytest.fixture
def pipeline_manager(client):
    return client.app.state.pipeline_manager


def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"


def test_status_endpoint_survives_malformed_stored_config(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '{"llm_api_key": "broken"'),
    )
    client.app.state.db.conn.commit()

    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["title"] == "Untitled Novel"


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
    response = client.post("/characters", json={
        "name": "Hero",
        "role": "Protagonist",
        "status": "active",
    })
    assert response.status_code == 200

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


def test_generate_outline_uses_stored_project_brief(client):
    project = client.post("/api/projects", json={
        "title": "Stored Brief Novel",
        "genre": "xuanhuan",
        "summary": "少年误入仙门，在阴谋中成长。",
        "target_chapters": 6,
    }).json()["project"]
    activate_response = client.post(f"/api/projects/{project['id']}/activate")
    assert activate_response.status_code == 200

    response = client.post("/api/outlines/generate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["outline"]["title"] == "Stored Brief Novel"
    assert data["outline"]["summary"] == "少年误入仙门，在阴谋中成长。"
    assert data["outline"]["total_chapters"] == 6


def test_generate_outline_ignores_request_brief_when_project_brief_exists(client):
    project = client.post("/api/projects", json={
        "title": "Canonical Brief Novel",
        "genre": "xuanhuan",
        "summary": "以项目内保存的简介为准。",
        "target_chapters": 7,
    }).json()["project"]
    activate_response = client.post(f"/api/projects/{project['id']}/activate")
    assert activate_response.status_code == 200

    response = client.post("/api/outlines/generate", json={
        "title": "Wrong Title",
        "genre": "urban",
        "summary": "这是错误的请求体简介。",
        "total_chapters": 3,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["outline"]["title"] == "Canonical Brief Novel"
    assert data["outline"]["summary"] == "以项目内保存的简介为准。"
    assert data["outline"]["total_chapters"] == 7


def test_update_outline_uses_same_generation_semantics_as_generate(client):
    project = client.post("/api/projects", json={
        "title": "Update Outline Novel",
        "genre": "xuanhuan",
        "summary": "更新接口也应读取持久化项目简介。",
        "target_chapters": 4,
    }).json()["project"]
    activate_response = client.post(f"/api/projects/{project['id']}/activate")
    assert activate_response.status_code == 200

    response = client.put("/api/outlines", json={
        "title": "Wrong Update Title",
        "summary": "Wrong update summary",
        "total_chapters": 2,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Outline generated"
    assert data["mode"] == "fallback"
    assert data["outline"]["title"] == "Update Outline Novel"
    assert data["outline"]["summary"] == "更新接口也应读取持久化项目简介。"
    assert data["outline"]["total_chapters"] == 4


def test_get_outline(client):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 5,
    })
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

def test_run_chapter_via_api(client, pipeline_manager, monkeypatch):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 10,
    })
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })

    class FakeOrchestrator:
        async def run_chapter(self, chapter_num: int):
            return {"chapter_num": chapter_num, "status": "reviewed"}

        def _has_api_key(self):
            return True

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 200
    data = response.json()
    assert data["chapter_num"] == 1
    assert data["status"] == "reviewed"
    assert data["mode"] == "model"


def test_run_chapter_via_api_requires_real_model(client):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 10,
    })
    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 422
    assert "real llm configuration" in response.json()["detail"].lower()


def test_create_project_requires_summary(client):
    response = client.post("/api/projects", json={
        "title": "No Summary Project",
        "genre": "xuanhuan",
        "summary": "   ",
        "target_chapters": 12,
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "Project summary is required"


def test_get_active_project_returns_null_when_no_project_is_active(client):
    response = client.get("/api/projects/active")

    assert response.status_code == 200
    assert response.json() == {"project": None}


def test_activate_project_sets_active_project_cookie(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    response = client.post(f"/api/projects/{project['id']}/activate")

    assert response.status_code == 200
    assert response.cookies.get(ACTIVE_PROJECT_COOKIE) == project["id"]
    assert client.cookies.get(ACTIVE_PROJECT_COOKIE) == project["id"]
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_activate_project_cookie_is_not_secure_on_http_client(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    response = client.post(f"/api/projects/{project['id']}/activate")

    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


def test_activate_project_cookie_ignores_forwarded_proto_on_http_client(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    response = client.post(
        f"/api/projects/{project['id']}/activate",
        headers={"x-forwarded-proto": "https"},
    )

    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


def test_activate_project_cookie_is_secure_on_https_client(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app, base_url="https://testserver") as client:
        project = client.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]

        response = client.post(f"/api/projects/{project['id']}/activate")

        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"]


def test_deleted_active_project_clears_secure_cookie_on_https_client(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app, base_url="https://testserver") as client:
        project = client.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]

        assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
        client.app.state.project_manager.delete_project(project["id"])

        response = client.get("/api/chapters")

        assert response.status_code == 409
        assert "Secure" in response.headers["set-cookie"]
        assert client.cookies.get(ACTIVE_PROJECT_COOKIE) is None


def test_get_active_project_persists_within_same_client_session(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200

    response = client.get("/api/projects/active")

    assert response.status_code == 200
    active_project = response.json()["project"]
    assert active_project is not None
    assert active_project["id"] == project["id"]
    assert active_project["title"] == "Project A"
    assert active_project["summary"] == "Project A summary"
    assert "db_path" not in active_project


def test_project_activation_is_isolated_between_two_test_clients(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client_a, TestClient(app) as client_b:
        project_a = client_a.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]
        project_b = client_b.post("/api/projects", json={
            "title": "Project B",
            "genre": "sci-fi",
            "summary": "Project B summary",
        }).json()["project"]

        assert client_a.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
        assert client_b.post(f"/api/projects/{project_b['id']}/activate").status_code == 200

        active_a = client_a.get("/api/projects/active")
        active_b = client_b.get("/api/projects/active")

        assert active_a.status_code == 200
        assert active_b.status_code == 200
        assert active_a.json()["project"]["id"] == project_a["id"]
        assert active_b.json()["project"]["id"] == project_b["id"]


def test_activate_project_does_not_stop_running_pipeline_in_other_session(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client_a, TestClient(app) as client_b:
        project_a = client_a.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]
        project_b = client_b.post("/api/projects", json={
            "title": "Project B",
            "genre": "sci-fi",
            "summary": "Project B summary",
        }).json()["project"]

        assert client_a.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
        response = client_b.post(f"/api/projects/{project_b['id']}/activate")

        assert response.status_code == 200


def test_project_scoped_chapters_are_isolated_between_two_test_clients(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client_a, TestClient(app) as client_b:
        project_a = client_a.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]
        project_b = client_b.post("/api/projects", json={
            "title": "Project B",
            "genre": "sci-fi",
            "summary": "Project B summary",
        }).json()["project"]

        assert client_a.post(f"/api/projects/{project_a['id']}/activate").status_code == 200
        assert client_b.post(f"/api/projects/{project_b['id']}/activate").status_code == 200
        assert client_a.post("/api/chapters", json={"title": "A1", "content": "project a data"}).status_code == 200

        chapters_a = client_a.get("/api/chapters")
        chapters_b = client_b.get("/api/chapters")

        assert chapters_a.status_code == 200
        assert chapters_b.status_code == 200
        assert len(chapters_a.json()["chapters"]) == 1
        assert chapters_a.json()["chapters"][0]["title"] == "A1"
        assert chapters_b.json()["chapters"] == []


def test_get_active_project_clears_stale_deleted_project_cookie(client):
    project = client.post("/api/projects", json={
        "title": "Deleted Project",
        "genre": "fantasy",
        "summary": "Deleted Project summary",
    }).json()["project"]

    assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
    client.app.state.project_manager.delete_project(project["id"])

    response = client.get("/api/projects/active")

    assert response.status_code == 200
    assert response.json() == {"project": None}
    assert client.cookies.get(ACTIVE_PROJECT_COOKIE) is None


def test_deleted_active_project_is_rejected_by_project_scoped_routes(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
    client.app.state.project_manager.delete_project(project["id"])

    chapters_response = client.get("/api/chapters")

    assert chapters_response.status_code == 409
    assert chapters_response.json()["detail"] == "Active project is no longer available; please reselect a project"
    assert chapters_response.headers["set-cookie"].startswith(f"{ACTIVE_PROJECT_COOKIE}=")
    assert client.cookies.get(ACTIVE_PROJECT_COOKIE) is None


def test_delete_active_project_clears_session_selection_and_rejects_followup_project_routes(client):
    project = client.post("/api/projects", json={
        "title": "Project A",
        "genre": "fantasy",
        "summary": "Project A summary",
    }).json()["project"]

    assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
    assert client.post("/api/chapters", json={"title": "Only Chapter", "content": "project data"}).status_code == 200

    delete_response = client.delete(f"/api/projects/{project['id']}")
    active_response = client.get("/api/projects/active")
    chapters_response = client.get("/api/chapters")

    assert delete_response.status_code == 200
    assert client.cookies.get(ACTIVE_PROJECT_COOKIE) is None
    assert active_response.status_code == 200
    assert active_response.json() == {"project": None}
    assert chapters_response.status_code == 200
    assert chapters_response.json()["chapters"] == []


def test_run_chapter_via_api_returns_validation_error_when_outline_missing(client):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })
    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 400
    assert "outline" in response.json()["detail"].lower()


def test_run_chapter_via_api_returns_validation_error_when_out_of_range(client, pipeline_manager, monkeypatch):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 1,
    })
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })

    class FakeOrchestrator:
        async def run_chapter(self, chapter_num: int):
            raise ValueError("chapter 2 is out of range for outline with 1 chapters")

        def _has_api_key(self):
            return True

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    response = client.post("/api/pipeline/run-chapter/2")
    assert response.status_code == 400
    assert "out of range" in response.json()["detail"].lower()


def test_run_chapter_via_api_hides_internal_error_details(client, pipeline_manager, monkeypatch):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 1,
    })
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })

    class FakeOrchestrator:
        async def run_chapter(self, chapter_num: int):
            raise RuntimeError("upstream provider timeout: api-key=secret")

        def _has_api_key(self):
            return True

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    response = client.post("/api/pipeline/run-chapter/1")
    assert response.status_code == 500
    assert response.json()["detail"] == "Chapter generation failed"



def test_run_chapter_via_api_hides_internal_error_details_in_logs(client, pipeline_manager, monkeypatch, caplog):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 1,
    })
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })

    class FakeOrchestrator:
        async def run_chapter(self, chapter_num: int):
            raise RuntimeError("upstream provider timeout: api-key=secret")

        def _has_api_key(self):
            return True

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    with caplog.at_level(logging.ERROR):
        response = client.post("/api/pipeline/run-chapter/1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Chapter generation failed"
    assert "api-key=secret" not in caplog.text



def test_run_chapter_via_api_releases_sync_lock_when_orchestrator_creation_fails(client, pipeline_manager, monkeypatch):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 2,
    })
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    })

    calls = {"count": 0}

    class SuccessOrchestrator:
        async def run_chapter(self, chapter_num: int):
            return {"chapter_num": chapter_num, "status": "reviewed"}

        def _has_api_key(self):
            return True

    def fake_create_orchestrator(db):
        calls["count"] += 1
        if calls["count"] == 1:
            raise studio_api.HTTPException(status_code=422, detail="Invalid stored config")
        return SuccessOrchestrator()

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        fake_create_orchestrator,
    )

    first_response = client.post("/api/pipeline/run-chapter/1")
    second_response = client.post("/api/pipeline/run-chapter/2")

    assert first_response.status_code == 422
    assert first_response.json()["detail"] == "Invalid stored config"
    assert second_response.status_code == 200
    assert second_response.json()["chapter_num"] == 2
    assert second_response.json()["status"] == "reviewed"
    assert second_response.json()["mode"] == "model"


def test_run_batch_via_api(client):
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 10,
    })
    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 3,
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "A real LLM configuration is required before generating chapters"


def test_run_batch_via_api_requires_real_model(client):
    client.post("/api/outlines/generate", json={
        "title": "Strict Batch Test",
        "summary": "A clear summary",
        "total_chapters": 5,
    })

    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 2,
    })

    assert response.status_code == 422
    assert response.json()["detail"] == "A real LLM configuration is required before generating chapters"


def test_run_batch_via_api_returns_conflict_when_pipeline_is_busy(client, pipeline_manager):
    class FakeTask:
        def done(self):
            return False

    class FakeOrchestrator:
        status = {"running": True, "paused": False}

    runtime = pipeline_manager._runtime_for_db(client.app.state.db)
    runtime.task = FakeTask()
    runtime.orchestrator = FakeOrchestrator()

    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 3,
    })

    assert response.status_code == 409
    assert response.json()["detail"] == "Pipeline already running"



def test_run_batch_via_api_returns_validation_error_on_value_error(client, pipeline_manager, monkeypatch):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })
    class FakeOrchestrator:
        async def run_batch(self, start: int, end: int):
            raise ValueError("start_chapter must be less than or equal to end_chapter")

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 3,
        "end_chapter": 1,
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "start_chapter must be less than or equal to end_chapter"



def test_run_batch_via_api_propagates_http_exception(client, pipeline_manager, monkeypatch):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })
    class FakeOrchestrator:
        async def run_batch(self, start: int, end: int):
            raise studio_api.HTTPException(status_code=422, detail="Invalid batch range")

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 3,
    })

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid batch range"



def test_run_batch_via_api_hides_internal_error_details(client, pipeline_manager, monkeypatch, caplog):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })

    class FakeOrchestrator:
        async def run_batch(self, start: int, end: int):
            raise RuntimeError("upstream provider timeout: api-key=secret")

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: FakeOrchestrator(),
    )

    with caplog.at_level(logging.ERROR):
        response = client.post("/api/pipeline/run-batch", json={
            "start_chapter": 1,
            "end_chapter": 3,
        })

    assert response.status_code == 500
    assert response.json()["detail"] == "Batch generation failed"
    assert "api-key=secret" not in caplog.text



def test_run_batch_via_api_rejects_concurrent_sync_request(client, pipeline_manager, monkeypatch):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })

    entered = threading.Event()
    release = threading.Event()

    class SlowOrchestrator:
        async def run_batch(self, start: int, end: int):
            import asyncio

            entered.set()
            await asyncio.to_thread(release.wait, 5)
            return {start: {"status": "reviewed"}}

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        lambda db: SlowOrchestrator(),
    )

    responses: dict[str, object] = {}

    def first_request() -> None:
        responses["first"] = client.post("/api/pipeline/run-batch", json={
            "start_chapter": 1,
            "end_chapter": 1,
        })

    worker = threading.Thread(target=first_request)
    worker.start()
    assert entered.wait(timeout=5)

    second_response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 2,
        "end_chapter": 2,
    })
    release.set()
    worker.join(timeout=5)

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Pipeline already running"
    first_response = responses.get("first")
    assert first_response is not None
    assert first_response.status_code == 200



def test_run_batch_via_api_releases_sync_lock_when_orchestrator_creation_fails(client, pipeline_manager, monkeypatch):
    client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen3.6-plus",
    })

    calls = {"count": 0}

    class SuccessOrchestrator:
        async def run_batch(self, start: int, end: int):
            return {start: {"status": "reviewed"}}

    def fake_create_orchestrator(db):
        calls["count"] += 1
        if calls["count"] == 1:
            raise studio_api.HTTPException(status_code=422, detail="Invalid stored config")
        return SuccessOrchestrator()

    monkeypatch.setattr(
        pipeline_manager,
        "_create_orchestrator",
        fake_create_orchestrator,
    )

    first_response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 1,
        "end_chapter": 1,
    })
    second_response = client.post("/api/pipeline/run-batch", json={
        "start_chapter": 2,
        "end_chapter": 2,
    })

    assert first_response.status_code == 422
    assert first_response.json()["detail"] == "Invalid stored config"
    assert second_response.status_code == 200
    assert second_response.json()["results"]["2"]["status"] == "reviewed"



def test_pipeline_manager_start_chapter_rejects_when_sync_lock_is_held(client, monkeypatch):
    import asyncio

    manager = studio_api.PipelineManager()

    def should_not_create_orchestrator(_db):
        raise AssertionError("_create_orchestrator should not be called when sync lock is held")

    monkeypatch.setattr(manager, "_create_orchestrator", should_not_create_orchestrator)

    runtime = manager._runtime_for_db(client.app.state.db)
    assert runtime.sync_run_lock.acquire(blocking=False)
    try:
        result = asyncio.run(manager.start_chapter(1, client.app.state.db))
    finally:
        if runtime.sync_run_lock.locked():
            runtime.sync_run_lock.release()

    assert result == {"error": "Pipeline already running", "started": False}



def test_pipeline_manager_start_batch_rejects_when_sync_lock_is_held(client, monkeypatch):
    import asyncio

    manager = studio_api.PipelineManager()

    def should_not_create_orchestrator(_db):
        raise AssertionError("_create_orchestrator should not be called when sync lock is held")

    monkeypatch.setattr(manager, "_create_orchestrator", should_not_create_orchestrator)

    runtime = manager._runtime_for_db(client.app.state.db)
    assert runtime.sync_run_lock.acquire(blocking=False)
    try:
        result = asyncio.run(manager.start_batch(1, 2, client.app.state.db))
    finally:
        if runtime.sync_run_lock.locked():
            runtime.sync_run_lock.release()

    assert result == {"error": "Pipeline already running", "started": False}



def test_run_chapter_via_api_allows_concurrent_sync_requests_for_different_projects(tmp_path, monkeypatch):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client_a, TestClient(app) as client_b:
        pipeline_manager = app.state.pipeline_manager
        project_a = client_a.post("/api/projects", json={
            "title": "Project A",
            "genre": "fantasy",
            "summary": "Project A summary",
        }).json()["project"]
        project_b = client_b.post("/api/projects", json={
            "title": "Project B",
            "genre": "sci-fi",
            "summary": "Project B summary",
        }).json()["project"]

        for client, project in ((client_a, project_a), (client_b, project_b)):
            assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
            assert client.post("/api/outlines/generate", json={
                "title": project["title"],
                "summary": project["summary"],
                "total_chapters": 2,
            }).status_code == 200
            assert client.post("/api/config", json={
                "llm_api_key": "test-key",
                "llm_base_url": "https://api.openai.com/v1",
                "default_model": "qwen3.6-plus",
            }).status_code == 200

        entered_a = threading.Event()
        entered_b = threading.Event()
        release = threading.Event()

        class SlowOrchestrator:
            def __init__(self, label: str):
                self.label = label

            async def run_chapter(self, chapter_num: int):
                import asyncio

                if self.label == "A":
                    entered_a.set()
                else:
                    entered_b.set()
                await asyncio.to_thread(release.wait, 5)
                return {"chapter_num": chapter_num, "status": f"reviewed-{self.label}"}

            def _has_api_key(self):
                return True

        def fake_create_orchestrator(db):
            if db.db_path.endswith(f"{project_a['id']}.db"):
                return SlowOrchestrator("A")
            if db.db_path.endswith(f"{project_b['id']}.db"):
                return SlowOrchestrator("B")
            raise AssertionError(f"Unexpected db path: {db.db_path}")

        monkeypatch.setattr(pipeline_manager, "_create_orchestrator", fake_create_orchestrator)

        responses: dict[str, object] = {}

        def request_a() -> None:
            responses["a"] = client_a.post("/api/pipeline/run-chapter/1")

        def request_b() -> None:
            responses["b"] = client_b.post("/api/pipeline/run-chapter/1")

        worker_a = threading.Thread(target=request_a)
        worker_b = threading.Thread(target=request_b)
        worker_a.start()
        assert entered_a.wait(timeout=5)
        worker_b.start()
        assert entered_b.wait(timeout=5)
        release.set()
        worker_a.join(timeout=5)
        worker_b.join(timeout=5)

        response_a = responses.get("a")
        response_b = responses.get("b")
        assert response_a is not None
        assert response_b is not None
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        assert response_a.json()["status"] == "reviewed-A"
        assert response_b.json()["status"] == "reviewed-B"



def test_pipeline_status_via_api(client):
    response = client.get("/api/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


# --- WebSocket tests ---

def test_websocket_connection(client):
    """Test that WebSocket endpoint accepts connections."""
    with client.websocket_connect("/ws/pipeline") as ws:
        ws.send_text('{"action": "subscribe"}')
        data = ws.receive_json()
        assert data["type"] == "subscription_confirmed"


def test_websocket_receives_pipeline_events(client):
    """Test that WebSocket pushes pipeline progress events."""
    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 5,
    })

    with client.websocket_connect("/ws/pipeline") as ws:
        ws.send_text('{"action": "subscribe"}')
        ws.receive_json()
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


def test_api_status_survives_malformed_stored_config(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("config", '{"llm_api_key": "broken"'),
    )
    client.app.state.db.conn.commit()

    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["title"] == "Untitled Novel"


def test_api_status_includes_core_chain_readiness_fact(client, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["core_chain_readiness"] == {
        "project_brief_ready": False,
        "outline_ready": False,
        "real_model_ready": False,
        "chapter_ready": False,
    }


def test_active_project_payload_reuses_same_core_chain_readiness_as_status(client):
    project = client.post("/api/projects", json={
        "title": "Ready Project",
        "genre": "fantasy",
        "summary": "Ready summary",
        "target_chapters": 4,
    }).json()["project"]

    assert client.post(f"/api/projects/{project['id']}/activate").status_code == 200
    assert client.post("/api/outlines/generate", json={}).status_code == 200
    assert client.post("/api/config", json={
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.openai.com/v1",
        "default_model": "qwen3.6-plus",
    }).status_code == 200

    status_response = client.get("/api/status")
    active_project_response = client.get("/api/projects/active")

    assert status_response.status_code == 200
    assert active_project_response.status_code == 200
    readiness = status_response.json()["core_chain_readiness"]
    assert readiness == {
        "project_brief_ready": True,
        "outline_ready": True,
        "real_model_ready": True,
        "chapter_ready": True,
    }
    assert active_project_response.json()["project"]["core_chain_readiness"] == readiness


def test_project_payload_falls_back_to_false_readiness_when_project_config_is_malformed(client):
    created_project = client.post("/api/projects", json={
        "title": "Broken Config Project",
        "genre": "fantasy",
        "summary": "Ready summary",
        "target_chapters": 4,
    }).json()["project"]

    assert client.post(f"/api/projects/{created_project['id']}/activate").status_code == 200
    project_info = client.app.state.project_manager.get_project(created_project["id"])
    assert project_info is not None
    project_db = StateDB(project_info.db_path)
    try:
        project_db.conn.execute(
            "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
            ("config", '{"llm_api_key": "broken"'),
        )
        project_db.conn.commit()
    finally:
        project_db.close()

    active_project_response = client.get("/api/projects/active")
    projects_response = client.get("/api/projects")

    assert active_project_response.status_code == 200
    assert projects_response.status_code == 200
    assert active_project_response.json()["project"]["core_chain_readiness"] == {
        "project_brief_ready": False,
        "outline_ready": False,
        "real_model_ready": False,
        "chapter_ready": False,
    }
    listed_project = next(item for item in projects_response.json()["projects"] if item["id"] == created_project["id"])
    assert listed_project["core_chain_readiness"] == {
        "project_brief_ready": False,
        "outline_ready": False,
        "real_model_ready": False,
        "chapter_ready": False,
    }


def test_status_and_api_status_share_same_fallback_for_malformed_project_brief(client):
    client.app.state.db.conn.execute(
        "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
        ("project_brief", '{"title": "Broken Brief"'),
    )
    client.app.state.db.conn.commit()

    status_response = client.get("/status")
    api_status_response = client.get("/api/status")

    assert status_response.status_code == 200
    assert api_status_response.status_code == 200
    assert status_response.json() == api_status_response.json()
    assert api_status_response.json()["status"] == "error"


def test_api_status_clamps_current_chapter_when_all_chapters_completed(client):
    client.post("/api/outlines/generate", json={
        "title": "Complete Novel",
        "summary": "A complete story",
        "total_chapters": 3,
    })
    for chapter_num in range(1, 4):
        client.post("/api/chapters", json={"title": f"Chapter {chapter_num}", "content": "Done"})
        client.put(f"/api/chapters/{chapter_num}", json={"status": "reviewed"})

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert data["current_chapter"] == 3
    assert data["total_chapters"] == 3
    assert data["status"] == "completed"


def test_api_status_reflects_pipeline_runtime_state(client, pipeline_manager):
    class FakeTask:
        def done(self):
            return False

    class FakeOrchestrator:
        def __init__(self, running: bool, paused: bool):
            self.status = {"running": running, "paused": paused}

    runtime = pipeline_manager._runtime_for_db(client.app.state.db)
    runtime.task = FakeTask()
    runtime.orchestrator = FakeOrchestrator(running=True, paused=False)
    running_response = client.get("/api/status")
    assert running_response.status_code == 200
    assert running_response.json()["status"] == "running"

    runtime.orchestrator = FakeOrchestrator(running=False, paused=True)
    paused_response = client.get("/api/status")
    assert paused_response.status_code == 200
    assert paused_response.json()["status"] == "paused"


def test_api_status_is_idle_when_progress_exists_but_pipeline_is_not_running(client):
    client.post("/api/outlines/generate", json={
        "title": "Partial Novel",
        "summary": "A partial story",
        "total_chapters": 3,
    })
    client.post("/api/chapters", json={"title": "Chapter 1", "content": "Done"})
    client.put("/api/chapters/1", json={"status": "reviewed"})

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"
    assert data["current_chapter"] == 2


def test_api_status_uses_first_incomplete_chapter_not_completed_count(client):
    client.post("/api/outlines/generate", json={
        "title": "Sparse Novel",
        "summary": "A sparse story",
        "total_chapters": 3,
    })
    client.post("/api/chapters", json={"title": "Chapter 1", "content": "Draft"})
    client.post("/api/chapters", json={"title": "Chapter 2", "content": "Done"})
    client.put("/api/chapters/2", json={"status": "reviewed"})

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()
    assert data["current_chapter"] == 1
    assert data["status"] == "idle"


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

    client.post("/api/outlines/generate", json={
        "title": "Test",
        "summary": "A clear summary",
        "total_chapters": 5,
    })
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
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy", "summary": "Project A summary"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi", "summary": "Project B summary"}).json()["project"]

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
    project_a = client.post("/api/projects", json={"title": "Project A", "genre": "fantasy", "summary": "Project A summary"}).json()["project"]
    project_b = client.post("/api/projects", json={"title": "Project B", "genre": "sci-fi", "summary": "Project B summary"}).json()["project"]

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


def test_pipeline_status_is_isolated_between_two_project_sessions(tmp_path):
    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client_a, TestClient(app) as client_b:
        pipeline_manager = app.state.pipeline_manager
        project_a = client_a.post("/api/projects", json={"title": "Project A", "genre": "fantasy", "summary": "Project A summary"}).json()["project"]
        project_b = client_b.post("/api/projects", json={"title": "Project B", "genre": "sci-fi", "summary": "Project B summary"}).json()["project"]
        project_a_info = app.state.project_manager.get_project(project_a["id"])
        project_b_info = app.state.project_manager.get_project(project_b["id"])
        assert project_a_info is not None
        assert project_b_info is not None

        assert client_a.post(f"/api/projects/{project_a['id']}/activate").status_code == 200

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

        project_a_db = StateDB(project_a_info.db_path)
        try:
            runtime = pipeline_manager._runtime_for_db(project_a_db)
            runtime.task = FakeTask()
            runtime.orchestrator = FakeOrchestrator()

            assert client_a.get("/api/pipeline/status").json() == {
                "running": True,
                "paused": True,
                "task_alive": True,
            }

            assert client_b.post(f"/api/projects/{project_b['id']}/activate").status_code == 200

            assert client_a.get("/api/pipeline/status").json() == {
                "running": True,
                "paused": True,
                "task_alive": True,
            }
            assert client_b.get("/api/pipeline/status").json() == {
                "running": False,
                "paused": False,
                "task_alive": False,
            }
            assert client_b.get("/api/status").json()["status"] == "idle"
            assert client_b.get("/status").json()["status"] == "idle"
        finally:
            project_a_db.close()
