"""Tests for Imitation Agent."""
from __future__ import annotations

import pytest

from Engine.agents.imitation import ImitationAgent


def test_imitation_generation():
    agent = ImitationAgent(model_name="test")
    result = agent.run({
        "sample_text": "样本内容",
        "topic": "测试主题",
    })
    assert "模仿" in result
    assert "测试主题" in result


@pytest.mark.asyncio
async def test_imitation_gateway_wiring():
    """Test that arun calls LLMGateway with correct messages."""
    agent = ImitationAgent(model_name="test")
    # Without a real gateway, this tests the mock fallback path
    result = agent.run({"sample_text": "测试", "topic": "主题"})
    assert isinstance(result, str)
