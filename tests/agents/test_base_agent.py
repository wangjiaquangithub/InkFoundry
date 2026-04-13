"""Tests for BaseAgent interface."""
import pytest
from Engine.agents.base import BaseAgent


def test_base_agent_init():
    agent = BaseAgent("test_model", "test prompt")
    assert agent.model == "test_model"
    assert agent.system_prompt == "test prompt"


def test_base_agent_run_not_implemented():
    agent = BaseAgent("test_model", "test prompt")
    with pytest.raises(NotImplementedError):
        agent.run({})
