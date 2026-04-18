"""Tests for PipelineOrchestrator."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from Engine.core.event_bus import EventBus
from Engine.core.models import Outline
from Engine.core.orchestrator import PipelineOrchestrator
from Engine.core.state_db import StateDB


@pytest.fixture
def db():
    db = StateDB(":memory:")
    yield db
    db.close()


def _make_outline(total_chapters: int = 10, missing_summary_at: int | None = None) -> Outline:
    chapter_summaries = []
    for chapter_num in range(1, total_chapters + 1):
        summary = "" if chapter_num == missing_summary_at else f"第{chapter_num}章概要"
        chapter_summaries.append({
            "chapter_num": chapter_num,
            "summary": summary,
            "tension": min(10, 4 + chapter_num),
        })
    return Outline(
        title="Test",
        summary="Test outline",
        total_chapters=total_chapters,
        chapter_summaries=chapter_summaries,
        tension_curve=[chapter["tension"] for chapter in chapter_summaries],
    )


def test_orchestrator_init(db):
    """Test orchestrator initialization."""
    orb = PipelineOrchestrator(state_db=db)
    assert orb.state_db is db
    assert orb._running is False
    assert orb._paused is False


def test_orchestrator_run_chapter_saves_result(db):
    """Test that run_chapter saves the chapter to StateDB."""
    db.save_outline(_make_outline())

    orb = PipelineOrchestrator(state_db=db)
    result = asyncio.run(orb.run_chapter(chapter_num=1))

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

    db.save_outline(_make_outline())

    orb = PipelineOrchestrator(state_db=db, event_bus=bus)
    asyncio.run(orb.run_chapter(chapter_num=1))

    assert len(events) > 0
    event_types = [e.get("step", "") for e in events if isinstance(e, dict)]
    assert "starting" in event_types


def test_orchestrator_requires_outline_before_generating(db):
    """Test that chapter generation fails fast without an outline."""
    orb = PipelineOrchestrator(state_db=db)
    orb._run_writer = AsyncMock(return_value="draft")
    orb._run_editor = AsyncMock(return_value={"score": 80, "issues": []})
    orb._run_redteam = AsyncMock(return_value={"severity": "low", "feedback": "ok"})

    with pytest.raises(ValueError, match="outline"):
        asyncio.run(orb.run_chapter(chapter_num=1))

    orb._run_writer.assert_not_awaited()
    orb._run_editor.assert_not_awaited()
    orb._run_redteam.assert_not_awaited()


def test_orchestrator_rejects_chapter_out_of_range(db):
    """Test that chapter generation rejects requests beyond the outline range."""
    db.save_outline(_make_outline(total_chapters=2))
    orb = PipelineOrchestrator(state_db=db)
    orb._run_writer = AsyncMock(return_value="draft")

    with pytest.raises(ValueError, match="out of range"):
        asyncio.run(orb.run_chapter(chapter_num=3))

    orb._run_writer.assert_not_awaited()


def test_orchestrator_requires_chapter_summary(db):
    """Test that chapter generation requires a non-empty chapter summary."""
    db.save_outline(_make_outline(total_chapters=3, missing_summary_at=2))
    orb = PipelineOrchestrator(state_db=db)
    orb._run_writer = AsyncMock(return_value="draft")

    with pytest.raises(ValueError, match="chapter summary"):
        asyncio.run(orb.run_chapter(chapter_num=2))

    orb._run_writer.assert_not_awaited()


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
    db.save_outline(_make_outline())

    orb = PipelineOrchestrator(state_db=db)
    results = asyncio.run(orb.run_batch(start=1, end=3))

    assert 1 in results
    assert 2 in results
    assert 3 in results
    assert db.get_chapter(1) is not None
    assert db.get_chapter(2) is not None
    assert db.get_chapter(3) is not None
