"""Background daemon for automatic novel generation."""
from __future__ import annotations
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DaemonScheduler:
    """Schedules and runs background novel generation tasks."""

    def __init__(self):
        self._running = False
        self._task_queue: list[dict] = []
        self._current_task: Optional[dict] = None
        self._callbacks: list[Callable] = []
        self._lock = threading.Lock()

    def start(self):
        """Start the daemon in a background thread."""
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()

    def stop(self):
        """Stop the daemon."""
        self._running = False

    def add_task(self, task: dict):
        """Add a task to the queue."""
        with self._lock:
            self._task_queue.append(task)

    def on_complete(self, callback: Callable):
        """Register a callback for task completion."""
        self._callbacks.append(callback)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def queue_size(self) -> int:
        return len(self._task_queue)

    @property
    def current_task(self) -> Optional[dict]:
        return self._current_task

    def _run_loop(self):
        """Main daemon loop."""
        while self._running:
            with self._lock:
                if not self._task_queue:
                    time.sleep(1)
                    continue
                self._current_task = self._task_queue.pop(0)

            # Simulate task execution (in real impl, this calls the pipeline)
            for callback in self._callbacks:
                try:
                    callback(self._current_task)
                except Exception:
                    logger.exception("Callback failed for task %s", self._current_task)

            self._current_task = None
