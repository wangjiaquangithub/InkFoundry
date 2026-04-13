"""Tests for DirectorAgent."""
from Engine.agents.director import DirectorAgent


def test_detect_loop_returns_true():
    agent = DirectorAgent("model", "Control sandbox.")
    history = ["scene"] * 15
    assert agent.detect_loop(history) is True


def test_no_loop_short_history():
    agent = DirectorAgent("model", "prompt")
    history = ["scene"] * 3
    assert agent.detect_loop(history) is False


def test_run_returns_decision_log():
    agent = DirectorAgent("model", "prompt")
    result = agent.run({"scene": "Protagonist enters room."})
    assert "decision" in result
