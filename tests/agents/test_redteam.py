"""Tests for RedTeamAgent."""
from Engine.agents.redteam import RedTeamAgent


def test_redteam_returns_attack():
    agent = RedTeamAgent("model", "Attack the plot.")
    result = agent.run({"draft": "Some draft text"})
    assert "attack" in result


def test_redteam_finds_logic_hole():
    agent = RedTeamAgent("model", "prompt")
    result = agent.run({"draft": "Chapter 2 scene"})
    assert isinstance(result["attack"], str)
    assert len(result["attack"]) > 0
