"""Tests for WriterAgent."""
from Engine.agents.writer import WriterAgent


def test_writer_returns_draft():
    agent = WriterAgent("model", "prompt")
    result = agent.run({"chapter": 1})
    assert "Draft" in result


def test_writer_chapter_number():
    agent = WriterAgent("model", "prompt")
    result = agent.run({"chapter": 5})
    assert "5" in result


def test_writer_has_model():
    agent = WriterAgent("gpt-4", "Write novel scenes.")
    assert agent.model == "gpt-4"
    assert agent.system_prompt == "Write novel scenes."


def test_writer_accepts_gateway_parameter():
    """WriterAgent accepts optional gateway parameter."""
    agent = WriterAgent("model", "prompt", gateway=None)
    assert agent._gateway is None


def test_writer_gateway_is_lazy():
    """WriterAgent creates gateway lazily via _get_gateway()."""
    agent = WriterAgent("test-model", "prompt", api_key="test-key", base_url="http://test")
    # No gateway yet
    assert agent._gateway is None
    # _get_gateway creates one
    gw = agent._get_gateway()
    assert gw is not None
    assert gw.model == "test-model"


import asyncio
import pytest


@pytest.mark.asyncio
async def test_writer_arun_calls_gateway():
    """Test WriterAgent.arun() calls LLMGateway instead of returning stub."""

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Generated chapter content from LLM"

    agent = WriterAgent(model_name="test-model", system_prompt="Write a novel")
    agent._gateway = FakeGateway()

    result = await agent.arun({"chapter_num": 1, "tension_level": 5})
    assert result == "Generated chapter content from LLM"
    assert "stub" not in result.lower()


@pytest.mark.asyncio
async def test_writer_arun_uses_prompt_builder():
    """Test WriterAgent.arun() builds proper prompt messages."""
    captured_messages = None

    class FakeGateway:
        async def chat(self, messages, **kwargs):
            nonlocal captured_messages
            captured_messages = messages
            return "Chapter content"

    agent = WriterAgent(model_name="test-model", system_prompt="You are a writer")
    agent._gateway = FakeGateway()

    await agent.arun({"chapter_num": 3, "tension_level": 7})
    assert captured_messages is not None
    assert len(captured_messages) == 2
    assert captured_messages[0]["role"] == "system"
    assert captured_messages[1]["role"] == "user"
    assert "第3章" in captured_messages[1]["content"]
