"""Tests for Side Story Agent."""
from __future__ import annotations

import pytest

from Engine.agents.side_story import SideStoryAgent


@pytest.mark.asyncio
async def test_side_story_generation():
    agent = SideStoryAgent(model_name="test")
    result = await agent.run({
        "characters": ["张三", "李四"],
        "setting": "修仙世界",
    })
    assert "番外" in result
    assert "张三" in result or "李四" in result
