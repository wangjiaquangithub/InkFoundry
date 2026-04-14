"""Lightweight in-process event bus (pub/sub pattern)."""
from __future__ import annotations
import uuid
from typing import Callable


# Event type constants
EVENT_AGENT_STATUS = "agent_status"
EVENT_CHAPTER_COMPLETE = "chapter_complete"
EVENT_CHAPTER_FAILED = "chapter_failed"
EVENT_REVIEW_REQUIRED = "review_required"
EVENT_PIPELINE_PROGRESS = "pipeline_progress"


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[tuple[str, Callable]]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> str:
        token = str(uuid.uuid4())
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append((token, callback))
        return token

    def unsubscribe(self, token: str):
        for event_type, subscribers in self._subscribers.items():
            self._subscribers[event_type] = [
                (t, cb) for t, cb in subscribers if t != token
            ]

    def publish(self, event_type: str, data: dict):
        for token, callback in self._subscribers.get(event_type, []):
            callback(data)
