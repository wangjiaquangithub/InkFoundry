"""Tests for Token Tracker."""
from __future__ import annotations

from Engine.core.token_tracker import TokenTracker


def test_record_token_usage():
    tracker = TokenTracker()
    tracker.record("qwen-plus", 1000, 500, "writer_chapter_1")
    assert tracker.stats.total_requests == 1
    assert tracker.stats.total_tokens == 1500


def test_stats_aggregation():
    tracker = TokenTracker()
    tracker.record("qwen-plus", 1000, 500, "task_a")
    tracker.record("qwen-plus", 2000, 800, "task_b")
    tracker.record("claude-sonnet", 500, 300, "task_a")

    assert tracker.stats.total_requests == 3
    assert tracker.stats.total_tokens == 5100
    assert len(tracker.get_stats_by_model()) == 2


def test_stats_by_model():
    tracker = TokenTracker()
    tracker.record("model_a", 100, 50)
    tracker.record("model_b", 200, 100)
    stats = tracker.get_stats_by_model()
    assert stats["model_a"] == 150
    assert stats["model_b"] == 300


def test_stats_by_task():
    tracker = TokenTracker()
    tracker.record("model", 100, 50, "task_1")
    tracker.record("model", 200, 100, "task_1")
    tracker.record("model", 50, 25, "task_2")
    stats = tracker.get_stats_by_task()
    assert stats["task_1"] == 450
    assert stats["task_2"] == 75


def test_cost_estimate():
    tracker = TokenTracker()
    tracker.record("claude-sonnet", 1000, 500)
    assert tracker.stats.total_cost_estimate > 0


def test_reset():
    tracker = TokenTracker()
    tracker.record("model", 100, 50, "task")
    tracker.reset()
    assert tracker.stats.total_requests == 0
    assert tracker.stats.total_tokens == 0


def test_records_returns_copy():
    tracker = TokenTracker()
    tracker.record("model", 100, 50)
    records = tracker.records
    assert len(records) == 1
    tracker._records.clear()
    assert len(records) == 1  # Is a copy
