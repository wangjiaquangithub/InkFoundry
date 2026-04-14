"""Tests for VoiceSandbox."""
import pytest
from Engine.agents.voice_sandbox import VoiceSandbox


def test_voice_injection():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    prompt = sandbox.inject_prompt("Write a scene.")
    assert "风格:" in prompt


def test_voice_config_loaded():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    assert "style" in sandbox.config


def test_injected_prompt_contains_voice():
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    prompt = sandbox.inject_prompt("Write action scene.")
    assert "Write action scene." in prompt


def test_voice_sandbox_with_speech_patterns():
    from Engine.agents.voice_sandbox import VoiceSandbox
    import tempfile, os, yaml

    config = {
        "style": "default",
        "tone": "neutral",
        "pacing": "moderate",
        "vocabulary": "standard",
        "speech_patterns": ["使用短句", "经常反问"],
        "forbidden_words": ["不禁", "仿佛"],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    try:
        sandbox = VoiceSandbox(temp_path)
        prompt = sandbox.inject_prompt("Write a chapter.")
        assert "短句" in prompt
        assert "不禁" in prompt
    finally:
        os.unlink(temp_path)


def test_voice_sandbox_with_sensory_bias():
    from Engine.agents.voice_sandbox import VoiceSandbox
    import tempfile, os, yaml

    config = {
        "style": "default",
        "tone": "dark",
        "pacing": "slow",
        "sensory_bias": {"visual": 0.8, "auditory": 0.3},
        "forbidden_words": [],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    try:
        sandbox = VoiceSandbox(temp_path)
        prompt = sandbox.inject_prompt("Write.")
        assert "感官偏好" in prompt
        assert "visual" in prompt
    finally:
        os.unlink(temp_path)


def test_voice_sandbox_rejects_path_traversal():
    """HIGH: VoiceSandbox must reject path traversal attempts."""
    with pytest.raises(ValueError, match="(?i)path"):
        VoiceSandbox("../../../etc/passwd")
