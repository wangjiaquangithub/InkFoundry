"""Tests for EngineConfig — LLM configuration from environment variables."""
import pytest
from Engine.config import EngineConfig


def test_config_from_env(monkeypatch):
    """Test loading all config values from environment variables."""
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")
    monkeypatch.setenv("EDITOR_MODEL", "claude-sonnet")
    monkeypatch.setenv("REDTEAM_MODEL", "gpt-4o")
    monkeypatch.setenv("NAVIGATOR_MODEL", "qwen-turbo")

    cfg = EngineConfig.from_env()

    assert cfg.llm.api_key == "test-key-123"
    assert cfg.llm.base_url == "https://example.com/v1"
    assert cfg.llm.default_model == "qwen-turbo"
    assert cfg.role_models["writer"] == "qwen-plus"
    assert cfg.role_models["editor"] == "claude-sonnet"
    assert cfg.role_models["redteam"] == "gpt-4o"
    assert cfg.role_models["navigator"] == "qwen-turbo"


def test_config_missing_api_key(monkeypatch):
    """Test that missing LLM_API_KEY raises ValueError."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LLM_API_KEY"):
        EngineConfig.from_env()


def test_config_defaults(monkeypatch):
    """Test default values when only LLM_API_KEY is set."""
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)

    cfg = EngineConfig.from_env()

    assert cfg.llm.base_url == "https://api.openai.com/v1"
    assert cfg.llm.default_model == "qwen-plus"
    for role in ("writer", "editor", "redteam", "navigator", "director"):
        assert cfg.role_models[role] == "qwen-plus"


def test_to_router_config(monkeypatch):
    """Test router config generation."""
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")

    cfg = EngineConfig.from_env()
    rc = cfg.to_router_config()

    assert rc["api_key"] == "key"
    assert rc["base_url"] == "https://example.com/v1"
    assert rc["default_model"] == "qwen-turbo"
    assert rc["writer"] == "qwen-plus"
