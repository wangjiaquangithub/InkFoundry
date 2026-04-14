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


def test_redteam_accepts_gateway_parameter():
    """RedTeamAgent accepts optional gateway parameter."""
    agent = RedTeamAgent("model", "prompt", gateway=None)
    assert agent._gateway is None


def test_redteam_gateway_is_lazy():
    """RedTeamAgent creates gateway lazily via _get_gateway()."""
    agent = RedTeamAgent("test-model", "prompt", api_key="test-key", base_url="http://test")
    assert agent._gateway is None
    gw = agent._get_gateway()
    assert gw is not None
    assert gw.model == "test-model"


import pytest


@pytest.mark.asyncio
async def test_redteam_arun_calls_gateway():
    """Test RedTeamAgent.arun() calls LLMGateway instead of returning stub."""

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Plot hole found in chapter 3"

    agent = RedTeamAgent(model_name="test-model")
    agent._gateway = FakeGateway()

    result = await agent.arun({"content": "Some chapter content"})
    assert "Plot hole" in result["feedback"]
    assert result["severity"] == "high"


@pytest.mark.asyncio
async def test_redteam_arun_returns_attacks_list():
    """Test RedTeamAgent.arun() returns proper attack response structure."""

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Character motivation is weak in scene 2"

    agent = RedTeamAgent(model_name="test-model", system_prompt="Attack the plot")
    agent._gateway = FakeGateway()

    result = await agent.arun({"content": "Scene content"})
    assert "attacks" in result
    assert isinstance(result["attacks"], list)
    assert len(result["attacks"]) == 1
    assert "Character motivation" in result["attacks"][0]


@pytest.mark.asyncio
async def test_redteam_arun_builds_prompt():
    """Test RedTeamAgent.arun() builds proper prompt with content."""
    captured_messages = None

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            nonlocal captured_messages
            captured_messages = messages
            return "Found issue"

    agent = RedTeamAgent(model_name="test-model", system_prompt="You are adversarial")
    agent._gateway = FakeGateway()

    await agent.arun({"content": "The hero defeated the villain easily"})
    assert captured_messages is not None
    assert "The hero defeated the villain easily" in captured_messages[1]["content"]
