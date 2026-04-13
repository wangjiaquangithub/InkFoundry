"""Tests for Hierarchical Model Router."""
from Engine.utils.router import ModelRouter


def test_router_default_model():
    config = {"default_model": "qwen-plus"}
    router = ModelRouter(config)
    assert router.get_model("writer") == "qwen-plus"


def test_router_writer_high_importance():
    config = {
        "default_model": "qwen-plus",
        "climax_model": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="high") == "claude-opus"


def test_router_writer_low_importance():
    config = {
        "default_model": "qwen-plus",
        "climax_model": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="low") == "qwen-plus"


def test_router_editor_always_default():
    config = {
        "default_model": "qwen-plus",
        "climax_model": "claude-opus",
    }
    router = ModelRouter(config)
    # Editor is not a writer, so climax_model doesn't apply
    assert router.get_model("editor", importance="high") == "qwen-plus"
