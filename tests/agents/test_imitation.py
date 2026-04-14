"""Tests for Imitation Agent."""
from __future__ import annotations

import pytest

from Engine.agents.imitation import ImitationAgent


@pytest.mark.asyncio
async def test_imitation_generation():
    agent = ImitationAgent(model_name="test")
    result = await agent.run({
        "sample_text": "样本内容",
        "topic": "测试主题",
    })
    assert "模仿" in result
    assert "测试主题" in result
