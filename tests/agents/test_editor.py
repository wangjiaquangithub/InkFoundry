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


def test_editor_accepts_gateway_parameter():
    """EditorAgent accepts optional gateway parameter."""
    agent = EditorAgent("model", "prompt", gateway=None)
    assert agent._gateway is None


def test_editor_gateway_is_lazy():
    """EditorAgent creates gateway lazily via _get_gateway()."""
    agent = EditorAgent("test-model", "prompt", api_key="test-key", base_url="http://test")
    assert agent._gateway is None
    gw = agent._get_gateway()
    assert gw is not None
    assert gw.model == "test-model"


import pytest


@pytest.mark.asyncio
async def test_editor_arun_calls_gateway():
    """Test EditorAgent.arun() calls LLMGateway instead of returning stub."""

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Editor feedback: logic is good"

    agent = EditorAgent(model_name="test-model")
    agent._gateway = FakeGateway()

    result = await agent.arun({"content": "Some chapter content"})
    assert "logic is good" in result["feedback"]
    assert result["score"] == 75


@pytest.mark.asyncio
async def test_editor_arun_builds_prompt():
    """Test EditorAgent.arun() builds proper prompt with content."""
    captured_messages = None

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            nonlocal captured_messages
            captured_messages = messages
            return "Good style"

    agent = EditorAgent(model_name="test-model", system_prompt="You are an editor")
    agent._gateway = FakeGateway()

    await agent.arun({"content": "The cat sat on the mat"})
    assert captured_messages is not None
    assert "The cat sat on the mat" in captured_messages[1]["content"]
