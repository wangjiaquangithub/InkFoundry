"""Tests for EditorAgent and RedTeamAgent."""
from Engine.agents.editor import EditorAgent
from Engine.agents.redteam import RedTeamAgent


def test_editor_returns_score():
    agent = EditorAgent("model", "Check logic and style.")
    result = agent.run({"draft": "Some draft text"})
    assert "score" in result
    assert "issues" in result


def test_editor_default_score():
    agent = EditorAgent("model", "prompt")
    result = agent.run({"draft": "text"})
    assert isinstance(result["score"], int)


def test_redteam_returns_attack():
    agent = RedTeamAgent("model", "Attack the plot.")
    result = agent.run({"draft": "Some draft text"})
    assert "attack" in result
