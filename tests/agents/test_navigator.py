"""Tests for NavigatorAgent tension heatmap."""
from Engine.agents.navigator import NavigatorAgent


def test_navigator_forces_climax():
    nav = NavigatorAgent("model", "prompt")
    # Last 3 chapters were boring (low tension)
    card = nav.generate_task_card(chapter_num=5, history_tension=[2, 2, 2])
    assert card["tension_level"] >= 8


def test_navigator_normal_pacing():
    nav = NavigatorAgent("model", "prompt")
    card = nav.generate_task_card(chapter_num=3, history_tension=[5, 7, 6])
    assert card["tension_level"] < 8


def test_navigator_returns_chapter():
    nav = NavigatorAgent("model", "prompt")
    card = nav.generate_task_card(chapter_num=10, history_tension=[])
    assert card["chapter"] == 10


def test_navigator_has_model():
    nav = NavigatorAgent("gpt-4", "Navigate the plot.")
    assert nav.model == "gpt-4"
