"""Tests for Prompt Builder."""
from __future__ import annotations

from Engine.llm.prompt_builder import PromptBuilder


def test_prompt_builder_basic():
    builder = PromptBuilder("You are a novelist.")
    messages = builder.build()
    assert messages[0] == {"role": "system", "content": "You are a novelist."}


def test_prompt_builder_with_context():
    builder = PromptBuilder("You are a novelist.")
    builder.with_context("Previous chapter: Hero defeated the dragon.")
    messages = builder.build()
    assert len(messages) == 2
    assert messages[1]["role"] == "user"
    assert "Previous chapter" in messages[1]["content"]


def test_prompt_builder_chain():
    builder = (
        PromptBuilder("Write a chapter.")
        .with_context("Background info")
        .with_constraints(["No AI phrases", "Use sensory details"])
    )
    messages = builder.build()
    content = messages[1]["content"]
    assert "Background info" in content
    assert "No AI phrases" in content


def test_prompt_builder_with_voice():
    builder = PromptBuilder("Write a chapter.")
    builder.with_voice({
        "speech_patterns": ["uses short sentences"],
        "vocabulary": ["sword", "magic"],
        "sensory_bias": {"visual": 0.5},
        "forbidden_words": ["不禁", "仿佛"],
    })
    messages = builder.build()
    content = messages[0]["content"]
    assert "short sentences" in content
    assert "不禁" in content  # forbidden word mentioned in constraints


def test_prompt_builder_with_state_snapshot():
    builder = PromptBuilder("Write.")
    builder.with_state_snapshot({
        "characters": [{"name": "Zhang San", "status": "alive"}],
        "world": {"era": "fantasy"},
    })
    messages = builder.build()
    content = messages[1]["content"]
    assert "Zhang San" in content
    assert "fantasy" in content


def test_prompt_builder_returns_two_messages():
    builder = PromptBuilder("System prompt only.")
    messages = builder.build()
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
