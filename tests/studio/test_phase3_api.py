"""Tests for Phase 3 value-add features: daemon, import, side-story, imitation, style."""
import pytest
from fastapi.testclient import TestClient
from Studio.api import create_app


@pytest.fixture
def client(tmp_path):
    """Provide a test client with seed data."""
    app = create_app(
        seed_data=True,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as c:
        yield c


# --- Daemon API tests ---

def test_daemon_status_idle(client):
    response = client.get("/api/daemon/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


def test_daemon_start_and_stop(client):
    response = client.post("/api/daemon/start", json={
        "start_chapter": 1,
        "end_chapter": 3,
        "interval_seconds": 60,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["started"] is True

    response = client.post("/api/daemon/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["stopped"] is True


# --- Import API tests ---

def test_import_from_text(client):
    text = "第1章\n这是一个测试章节内容。\n\n第2章\n这是第二章的内容。"
    response = client.post("/api/import/text", json={
        "title": "Test Novel",
        "content": text,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Novel"
    assert len(data["chapters"]) == 2


def test_import_and_apply(client):
    text = "第1章\n这是导入并应用的章节内容。"
    response = client.post("/api/import/apply", json={
        "title": "Imported Novel",
        "content": text,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 1

    # Verify chapter was saved to StateDB
    response = client.get("/api/chapters")
    assert len(response.json()["chapters"]) >= 1


def test_import_empty_text(client):
    response = client.post("/api/import/text", json={
        "title": "Empty",
        "content": "",
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["chapters"]) == 0


# --- Side Story API tests ---

def test_generate_side_story(client):
    response = client.post("/api/side-story/generate", json={
        "characters": ["Hero", "Mentor"],
        "setting": "远古大陆",
        "topic": "师徒之间的日常",
    })
    assert response.status_code == 200
    data = response.json()
    assert "content" in data


# --- Imitation API tests ---

def test_generate_imitation(client):
    response = client.post("/api/imitation/generate", json={
        "sample_text": "他走进了房间，仿佛回到了过去。",
        "topic": "新的冒险",
    })
    assert response.status_code == 200
    data = response.json()
    assert "content" in data


# --- Style API tests ---

def test_extract_style(client):
    text = "他走进了房间，仿佛回到了过去。然而，他并不知道等待他的是什么。"
    response = client.post("/api/style/extract", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert "avg_sentence_length" in data
    assert "tone" in data
    assert "common_patterns" in data


def test_style_fingerprint(client):
    text = "他走进了房间，仿佛回到了过去。然而，他并不知道等待他的是什么。"
    response = client.post("/api/style/fingerprint", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert "fingerprint" in data
    assert "style_profile" in data
