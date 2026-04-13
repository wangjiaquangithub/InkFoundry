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
