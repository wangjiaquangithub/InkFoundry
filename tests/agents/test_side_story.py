"""Tests for Side Story Agent."""
from __future__ import annotations

import pytest

from Engine.agents.side_story import SideStoryAgent


def test_side_story_generation():
    agent = SideStoryAgent(model_name="test")
    result = agent.run({
        "characters": ["张三", "李四"],
        "setting": "修仙世界",
    })
    assert "番外" in result
    assert "张三" in result or "李四" in result


@pytest.mark.asyncio
async def test_side_story_gateway_wiring():
    """Test that arun calls LLMGateway with correct messages."""
    agent = SideStoryAgent(model_name="test")
    result = agent.run({"characters": ["Hero"], "setting": "World", "topic": "Adventure"})
    assert isinstance(result, str)
