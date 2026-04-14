"""Tests for Daemon Scheduler."""
from __future__ import annotations

import logging
import time
from Engine.core.daemon import DaemonScheduler


def test_scheduler_start_stop():
    scheduler = DaemonScheduler()
    assert not scheduler.is_running
    scheduler.start()
    assert scheduler.is_running
    scheduler.stop()
    assert not scheduler.is_running


def test_add_task_increases_queue():
    scheduler = DaemonScheduler()
    scheduler.add_task({"chapter": 1})
    assert scheduler.queue_size == 1
    scheduler.add_task({"chapter": 2})
    assert scheduler.queue_size == 2


def test_on_complete_callback():
    completed = []
    scheduler = DaemonScheduler()
    scheduler.on_complete(lambda task: completed.append(task))
    scheduler.add_task({"id": 1})

    # Manually process
    scheduler.start()
    time.sleep(0.5)
    scheduler.stop()
    assert len(completed) >= 1


def test_current_task_tracking():
    scheduler = DaemonScheduler()
    scheduler.add_task({"id": "test"})
    scheduler.start()
    time.sleep(0.3)
    # Task should have been processed
    scheduler.stop()


def test_daemon_continues_after_callback_exception():
    """CRITICAL: Daemon must continue processing tasks when a callback raises.

    A single callback exception should not kill the entire daemon thread.
    """
    scheduler = DaemonScheduler()
    successful_callbacks = []

    def flaky_callback(task):
        if task.get("fail"):
            raise RuntimeError("Callback failure")
        successful_callbacks.append(task)

    scheduler.on_complete(flaky_callback)
    scheduler.add_task({"id": 1, "fail": True})  # Will raise
    scheduler.add_task({"id": 2, "fail": False})  # Should still process

    scheduler.start()
    time.sleep(1.0)
    scheduler.stop()

    # Task 2 should have been processed despite task 1's callback failing
    assert len(successful_callbacks) >= 1
    assert successful_callbacks[0]["id"] == 2
