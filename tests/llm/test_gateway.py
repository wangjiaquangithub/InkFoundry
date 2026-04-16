"""Tests for LLM Gateway."""
from __future__ import annotations

import pytest

from Engine.llm.gateway import LLMGateway


def test_gateway_init():
    gw = LLMGateway(model="qwen3.6-plus", api_key="test-key", base_url="https://example.com/v1")
    assert gw.model == "qwen3.6-plus"
    assert gw.api_key == "test-key"
    assert gw.base_url == "https://example.com/v1"


@pytest.mark.asyncio
async def test_gateway_chat_returns_content(monkeypatch):
    """Test that chat returns content from API response."""
    gw = LLMGateway("test-model", "key", "https://example.com/v1")

    class FakeChoice:
        class Message:
            content = "Hello from LLM"
        message = Message()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        async def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    gw._client = FakeClient()

    result = await gw.chat([{"role": "user", "content": "hi"}])
    assert result == "Hello from LLM"


@pytest.mark.asyncio
async def test_gateway_chat_retries_on_failure(monkeypatch):
    """Test that chat retries on API failure with exponential backoff."""
    gw = LLMGateway("test-model", "key", "https://example.com/v1")
    call_count = 0

    class FakeCompletions:
        async def create(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("API down")
            return type("Response", (), {"choices": [type("Choice", (), {"message": type("Msg", (), {"content": "retry success"})()})()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    gw._client = FakeClient()

    result = await gw.chat([{"role": "user", "content": "hi"}])
    assert result == "retry success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_gateway_chat_raises_after_all_retries(monkeypatch):
    """Test that chat raises after 5 failed retries."""
    gw = LLMGateway("test-model", "key", "https://example.com/v1")

    class FakeCompletions:
        async def create(self, **kwargs):
            raise ConnectionError("always down")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    gw._client = FakeClient()

    with pytest.raises(ConnectionError, match="always down"):
        await gw.chat([{"role": "user", "content": "hi"}])
