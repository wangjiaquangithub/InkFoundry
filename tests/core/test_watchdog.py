"""Tests for Watchdog Timer."""
from __future__ import annotations

import threading
import time

from Engine.core.controller import WatchdogTimer


def test_watchdog_starts_and_stops():
    wd = WatchdogTimer(timeout_seconds=1)
    wd.start("test_step")
    wd.stop()
    assert not wd.timed_out


def test_watchdog_resets_timer():
    wd = WatchdogTimer(timeout_seconds=1)
    wd.start("test_step")
    time.sleep(0.1)
    wd.reset()
    time.sleep(0.2)
    wd.stop()
    assert not wd.timed_out


def test_watchdog_times_out():
    wd = WatchdogTimer(timeout_seconds=0.5)
    wd.start("slow_step")
    time.sleep(0.7)
    assert wd.timed_out
    wd.stop()


def test_watchdog_sends_events():
    events = []

    class FakeBus:
        def publish(self, event_type, data):
            events.append((event_type, data))

    wd = WatchdogTimer(timeout_seconds=0.5, event_bus=FakeBus())
    wd.start("test_step")
    assert len(events) == 1
    assert events[0][1]["step"] == "test_step"
    assert events[0][1]["status"] == "started"
    wd.stop()


def test_watchdog_timed_out_thread_safe():
    """CRITICAL: timed_out property must be thread-safe.

    The timeout callback runs on a different thread than the main thread
    reading timed_out. Uses threading.Event for synchronization.
    """
    wd = WatchdogTimer(timeout_seconds=0.2)
    wd.start("slow_step")
    # Wait for timeout to fire
    time.sleep(0.4)
    # Multiple concurrent reads should all see consistent value
    results = []
    barrier = threading.Barrier(5)

    def reader():
        barrier.wait()
        results.append(wd.timed_out)

    threads = [threading.Thread(target=reader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(results)
    wd.stop()
