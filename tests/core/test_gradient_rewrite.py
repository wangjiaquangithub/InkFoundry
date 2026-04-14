"""Tests for Gradient Rewrite Protocol."""
from __future__ import annotations

import pytest
from Engine.core.controller import GradientRewriter


class FakeGateway:
    async def chat(self, messages, **kwargs):
        return f"Rewritten content with temperature={kwargs.get('temperature', 0)}"


@pytest.mark.asyncio
async def test_rewrite_patch_paragraph():
    """Retry 0: localized paragraph fix with low temperature."""
    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway)
    draft = {"content": "Original chapter content"}
    error = {"error": "Logic inconsistency in paragraph 3"}

    result = await rewriter.rewrite(draft, error, retry_num=0)
    assert "temperature=0.3" in result
    assert "Rewritten content" in result


@pytest.mark.asyncio
async def test_rewrite_recontext_state():
    """Retry 1: full chapter rewrite with State_Snapshot context."""
    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway)
    draft = {"content": "Original chapter"}
    error = {
        "error": "Character status mismatch",
        "state_snapshot": {
            "characters": [{"name": "Zhang San", "status": "alive"}],
            "world": {"era": "fantasy"},
        },
    }

    result = await rewriter.rewrite(draft, error, retry_num=1)
    assert "temperature=0.5" in result


@pytest.mark.asyncio
async def test_rewrite_pivot():
    """Retry 2+: plot pivot with high temperature for creative divergence."""
    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway)
    draft = {"content": "Original chapter"}
    error = {"error": "Plot hole"}

    result = await rewriter.rewrite(draft, error, retry_num=2)
    assert "temperature=0.8" in result


@pytest.mark.asyncio
async def test_rewrite_sends_event():
    """Rewrite should publish a gradient_rewrite event when event_bus is provided."""
    gateway = FakeGateway()
    events = []

    class FakeBus:
        def publish(self, event, data):
            events.append((event, data))

    bus = FakeBus()
    rewriter = GradientRewriter(gateway, event_bus=bus)
    draft = {"content": "Chapter"}
    error = {"error": "Test error"}

    await rewriter.rewrite(draft, error, retry_num=0)
    assert any("rewrite" in str(e[0]).lower() for e in events)
    assert events[0][1]["retry_num"] == 0
    assert events[0][1]["error"] == "Test error"


@pytest.mark.asyncio
async def test_rewrite_no_event_without_bus():
    """Rewrite should not crash when event_bus is None."""
    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway, event_bus=None)
    draft = {"content": "Chapter"}
    error = {"error": "Test error"}

    result = await rewriter.rewrite(draft, error, retry_num=0)
    assert "Rewritten content" in result


@pytest.mark.asyncio
async def test_rewrite_high_retry_numbers():
    """Retry numbers beyond 2 should still use pivot strategy."""
    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway)
    draft = {"content": "Original chapter"}
    error = {"error": "Persistent failure"}

    for retry_num in [3, 4, 5]:
        result = await rewriter.rewrite(draft, error, retry_num=retry_num)
        assert "temperature=0.8" in result
