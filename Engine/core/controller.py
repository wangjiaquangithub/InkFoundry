"""Pipeline Controller with watchdog and circuit breaker."""
from __future__ import annotations

from typing import Any, Callable


class CircuitBreakerError(Exception):
    """Raised when max retries are exhausted."""
    pass


class PipelineController:
    """Manages task execution with retry logic and graceful degradation.

    Args:
        max_retries: Maximum number of retry attempts before circuit breaker trips.
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def execute_with_retry(
        self,
        task_func: Callable,
        *args: Any,
        graceful_degradation: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Execute a task with retry logic.

        On the final attempt:
        - If graceful_degradation is True, return a fallback dict instead of raising.
        - Otherwise, raise CircuitBreakerError.
        """
        attempts = 0
        while attempts < self.max_retries:
            try:
                return task_func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if attempts >= self.max_retries:
                    if graceful_degradation:
                        return {
                            "status": "degraded",
                            "error": str(e),
                            "attempts": attempts,
                        }
                    raise CircuitBreakerError(
                        f"Max retries ({self.max_retries}) reached. Last error: {e}"
                    )
