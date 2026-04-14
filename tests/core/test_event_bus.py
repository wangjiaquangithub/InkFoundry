"""Tests for Event Bus."""
from __future__ import annotations

from Engine.core.event_bus import EventBus


def test_event_bus_publish_subscribe():
    bus = EventBus()
    results = []
    bus.subscribe("test_event", lambda data: results.append(data))
    bus.publish("test_event", {"value": 42})
    assert results == [{"value": 42}]


def test_event_bus_multiple_subscribers():
    bus = EventBus()
    results = []
    bus.subscribe("evt", lambda d: results.append(1))
    bus.subscribe("evt", lambda d: results.append(2))
    bus.publish("evt", {})
    assert results == [1, 2]


def test_event_bus_unsubscribe():
    bus = EventBus()
    results = []
    callback = lambda d: results.append("called")
    token = bus.subscribe("evt", callback)
    bus.publish("evt", {})
    assert results == ["called"]
    bus.unsubscribe(token)
    results.clear()
    bus.publish("evt", {})
    assert results == []


def test_event_bus_different_events():
    bus = EventBus()
    results_a, results_b = [], []
    bus.subscribe("event_a", lambda d: results_a.append(d))
    bus.subscribe("event_b", lambda d: results_b.append(d))
    bus.publish("event_a", {"x": 1})
    bus.publish("event_b", {"y": 2})
    assert results_a == [{"x": 1}]
    assert results_b == [{"y": 2}]
