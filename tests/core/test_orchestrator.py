"""Tests for PipelineOrchestrator."""
import pytest

from Engine.core.orchestrator import PipelineOrchestrator
from Engine.core.state_db import StateDB
from Engine.core.event_bus import EventBus
from Engine.core.models import Chapter, Outline


@pytest.fixture
def db():
    db = StateDB(":memory:")
    yield db
    db.close()


def test_orchestrator_init(db):
    """Test orchestrator initialization."""
    orb = PipelineOrchestrator(state_db=db)
    assert orb.state_db is db
    assert orb._running is False
    assert orb._paused is False


def test_orchestrator_run_chapter_saves_result(db):
    """Test that run_chapter saves the chapter to StateDB."""
    outline = Outline(title="Test", summary="Test", total_chapters=10)
    db.save_outline(outline)

    orb = PipelineOrchestrator(state_db=db)
    result = orb.run_chapter(chapter_num=1)

    assert result is not None
    assert "status" in result
    chapter = db.get_chapter(1)
    assert chapter is not None
    assert chapter.chapter_num == 1


def test_orchestrator_run_chapter_publishes_events(db):
    """Test that run_chapter publishes events."""
    events = []
    bus = EventBus()
    bus.subscribe("pipeline_progress", lambda data: events.append(data))
    bus.subscribe("chapter_complete", lambda data: events.append(data))

    outline = Outline(title="Test", summary="Test", total_chapters=10)
    db.save_outline(outline)

    orb = PipelineOrchestrator(state_db=db, event_bus=bus)
    orb.run_chapter(chapter_num=1)

    assert len(events) > 0
    # Should have at least a starting event
    event_types = [e.get("step", "") for e in events if isinstance(e, dict)]
    assert "starting" in event_types


def test_orchestrator_status(db):
    """Test status reporting."""
    orb = PipelineOrchestrator(state_db=db)
    status = orb.status
    assert status["running"] is False
    assert status["paused"] is False
    assert status["current_chapter"] == 0


def test_orchestrator_pause_resume(db):
    """Test pause and resume."""
    orb = PipelineOrchestrator(state_db=db)
    assert orb._paused is False
    orb.pause()
    assert orb._paused is True
    orb.resume()
    assert orb._paused is False


def test_orchestrator_stop(db):
    """Test stop."""
    orb = PipelineOrchestrator(state_db=db)
    orb._running = True
    orb.stop()
    assert orb._running is False
    assert orb._paused is False


def test_orchestrator_run_batch(db):
    """Test run_batch for multiple chapters."""
    outline = Outline(title="Test", summary="Test", total_chapters=10)
    db.save_outline(outline)

    orb = PipelineOrchestrator(state_db=db)
    results = orb.run_batch(start=1, end=3)

    assert 1 in results
    assert 2 in results
    assert 3 in results
    assert db.get_chapter(1) is not None
    assert db.get_chapter(2) is not None
    assert db.get_chapter(3) is not None
