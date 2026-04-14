"""Tests for BaseAgent interface."""
import pytest
from Engine.agents.base import BaseAgent


def test_base_agent_init():
    agent = BaseAgent("test_model", "test prompt")
    assert agent.model == "test_model"
    assert agent.system_prompt == "test prompt"
    assert agent.api_key == ""
    assert agent.base_url == "https://api.openai.com/v1"


def test_base_agent_init_with_credentials():
    agent = BaseAgent(
        "test_model",
        "test prompt",
        api_key="secret-key",
        base_url="https://example.com/v1",
    )
    assert agent.api_key == "secret-key"
    assert agent.base_url == "https://example.com/v1"


def test_base_agent_run_not_implemented():
    agent = BaseAgent("test_model", "test prompt")
    with pytest.raises(NotImplementedError):
        agent.run({})


def test_base_agent_build_client_returns_openai():
    """Test _build_client returns an OpenAI client when package is available."""
    agent = BaseAgent("test_model", "test prompt", api_key="key", base_url="https://example.com/v1")
    client = agent._build_client()
    assert client is not None
    assert client.api_key == "key"


def test_base_agent_from_router_info():
    """Test creating agent from ModelInfo dict."""
    agent = BaseAgent.from_router_info(
        {
            "model": "qwen-plus",
            "api_key": "key",
            "base_url": "https://example.com/v1",
        },
        system_prompt="Write novel.",
    )
    assert agent.model == "qwen-plus"
    assert agent.api_key == "key"
    assert agent.base_url == "https://example.com/v1"
