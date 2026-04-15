"""Tests for OutlineAgent."""
import pytest

from Engine.agents.outline import OutlineAgent
from Engine.core.models import Outline


def test_outline_agent_returns_structure():
    """Test that OutlineAgent returns a structured outline."""
    agent = OutlineAgent()
    outline = agent.run(
        genre="xuanhuan",
        title="Test Novel",
        summary="A hero's journey",
        total_chapters=10,
    )
    assert outline is not None
    assert outline.title == "Test Novel"
    assert len(outline.chapter_summaries) > 0
    assert len(outline.tension_curve) > 0


def test_outline_agent_chapter_count_matches():
    """Test that chapter summaries match requested total."""
    agent = OutlineAgent()
    outline = agent.run(genre="xianxia", title="Cultivation", total_chapters=5)
    assert len(outline.chapter_summaries) == 5
    assert len(outline.tension_curve) == 5


def test_outline_agent_genre_rules():
    """Test that genre-specific rules are included."""
    agent = OutlineAgent()
    outline = agent.run(genre="xuanhuan", title="Test", total_chapters=5)
    assert len(outline.genre_rules) > 0
    assert "战力不能倒退" in outline.genre_rules


def test_outline_agent_xianxia_rules():
    """Test xianxia genre rules."""
    agent = OutlineAgent()
    outline = agent.run(genre="xianxia", title="Test", total_chapters=5)
    assert "修炼等级递进" in outline.genre_rules


def test_outline_agent_urban_rules():
    """Test urban genre rules."""
    agent = OutlineAgent()
    outline = agent.run(genre="urban", title="Test", total_chapters=5)
    assert "现实逻辑" in outline.genre_rules


def test_outline_agent_scifi_rules():
    """Test scifi genre rules."""
    agent = OutlineAgent()
    outline = agent.run(genre="scifi", title="Test", total_chapters=5)
    assert "科技自洽" in outline.genre_rules


def test_outline_agent_wuxia_rules():
    """Test wuxia genre rules."""
    agent = OutlineAgent()
    outline = agent.run(genre="wuxia", title="Test", total_chapters=5)
    assert "武功招式描写" in outline.genre_rules


def test_outline_agent_volume_plans():
    """Test that volume plans are generated."""
    agent = OutlineAgent()
    outline = agent.run(genre="xuanhuan", title="Test", total_chapters=100)
    assert len(outline.volume_plans) == 4


def test_outline_agent_default_values():
    """Test default outline values."""
    agent = OutlineAgent()
    outline = agent.run()
    assert outline.title == "Untitled"
    assert outline.arc == "hero_journey"
