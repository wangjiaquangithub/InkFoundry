"""Tests for Hierarchical Model Router."""
from Engine.utils.router import ModelRouter


def test_router_default_model():
    config = {"default_model": "qwen3.6-plus"}
    router = ModelRouter(config)
    assert router.get_model("writer")["model"] == "qwen3.6-plus"


def test_router_writer_high_importance():
    config = {
        "default_model": "qwen3.6-plus",
        "writer": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="high")["model"] == "claude-opus"


def test_router_writer_low_importance():
    config = {
        "default_model": "qwen3.6-plus",
        "writer": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="low")["model"] == "qwen3.6-plus"


def test_router_editor_always_default():
    config = {
        "default_model": "qwen3.6-plus",
        "editor": "claude-sonnet",
    }
    router = ModelRouter(config)
    assert router.get_model("editor", importance="high")["model"] == "claude-sonnet"


def test_router_returns_credentials():
    """Test that get_model returns dict with api_key and base_url."""
    config = {
        "default_model": "qwen3.6-plus",
        "api_key": "secret-key",
        "base_url": "https://api.example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("editor")

    assert result["model"] == "qwen3.6-plus"
    assert result["api_key"] == "secret-key"
    assert result["base_url"] == "https://api.example.com/v1"


def test_router_writer_high_importance_with_credentials():
    """Test writer gets role-specific model when importance is high."""
    config = {
        "default_model": "qwen3.6-plus",
        "writer": "qwen-max",
        "api_key": "key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("writer", importance="high")

    assert result["model"] == "qwen-max"
    assert result["api_key"] == "key"
    assert result["base_url"] == "https://example.com/v1"
