"""Tests for VoiceSandbox."""
import pytest
from Engine.agents.voice_sandbox import VoiceSandbox


def test_voice_injection():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    prompt = sandbox.inject_prompt("Write a scene.")
    assert "Style:" in prompt


def test_voice_config_loaded():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    assert "style" in sandbox.config


def test_injected_prompt_contains_voice():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    prompt = sandbox.inject_prompt("Write action scene.")
    assert "Write action scene." in prompt
