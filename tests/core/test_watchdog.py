"""Tests for Watchdog Timer."""
from __future__ import annotations

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
