"""Pipeline Controller with watchdog, circuit breaker, and Gradient Rewrite Protocol."""
from __future__ import annotations

import threading
import time
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


class GradientRewriter:
    """3-tier retry strategy for failed chapter rewrites.

    Retry 0: Localized patch — fix a single problematic paragraph.
    Retry 1: Re-context with State_Snapshot — full chapter rewrite with state context.
    Retry 2+: Pivot strategy — propose an entirely different plot direction.
    """

    def __init__(self, gateway, event_bus=None):
        self._gateway = gateway
        self._event_bus = event_bus

    async def rewrite(self, draft: dict, error_context: dict, retry_num: int) -> str:
        """Route to the appropriate rewrite strategy based on retry number."""
        if retry_num == 0:
            result = await self._patch_paragraph(draft, error_context)
        elif retry_num == 1:
            result = await self._recontext_with_state(draft, error_context)
        else:
            result = await self._pivot_strategy(draft, error_context)

        if self._event_bus is not None:
            self._event_bus.publish(
                "gradient_rewrite",
                {
                    "retry_num": retry_num,
                    "error": error_context.get("error", "unknown"),
                    "result_preview": result[:100],
                },
            )

        return result

    async def _patch_paragraph(self, draft: dict, error_context: dict) -> str:
        """Retry 0: Localized patch fix for a single paragraph."""
        content = draft.get("content", "")
        error_desc = error_context.get("error", "unknown error")

        # Lazy import to avoid hard dependency when gateway is a fake
        from Engine.llm.prompt_builder import PromptBuilder

        builder = PromptBuilder("你是一个小说编辑。修复以下章节中的问题段落。")
        builder.with_context(
            f"原始内容:\n{content}\n\n问题描述: {error_desc}\n\n请修复问题段落，保持原文风格。"
        )
        messages = builder.build()

        result = await self._gateway.chat(messages, temperature=0.3, max_tokens=2048)
        return result

    async def _recontext_with_state(self, draft: dict, error_context: dict) -> str:
        """Retry 1: Full chapter rewrite with State_Snapshot context."""
        content = draft.get("content", "")
        error_desc = error_context.get("error", "unknown error")
        state_snapshot = error_context.get("state_snapshot", {})

        from Engine.llm.prompt_builder import PromptBuilder

        builder = PromptBuilder("你是一个小说编辑。根据当前角色和世界状态，重写以下章节。")
        builder.with_state_snapshot(state_snapshot)
        builder.with_context(
            f"原始内容:\n{content}\n\n问题描述: {error_desc}\n\n请在保持状态一致性的前提下重写章节。"
        )
        messages = builder.build()

        result = await self._gateway.chat(messages, temperature=0.5, max_tokens=4096)
        return result

    async def _pivot_strategy(self, draft: dict, error_context: dict) -> str:
        """Retry 2+: Plot pivot — propose an alternative direction and rewrite."""
        content = draft.get("content", "")
        error_desc = error_context.get("error", "unknown error")

        from Engine.llm.prompt_builder import PromptBuilder

        builder = PromptBuilder(
            "你是一个小说策划。以下章节存在严重问题，请提出一个完全不同的剧情方向并重写。"
        )
        builder.with_context(
            f"原始内容:\n{content}\n\n问题描述: {error_desc}\n\n请提出一个新的剧情方向并重写章节。"
        )
        messages = builder.build()

        result = await self._gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return result


class WatchdogTimer:
    """Kills pipeline if a single step takes too long.

    Monitors execution time per step and publishes timeout events
    to the EventBus when a step exceeds the configured timeout.

    Args:
        timeout_seconds: Maximum time allowed for a single step (default: 300s / 5min).
        event_bus: Optional EventBus instance for publishing progress events.
    """

    def __init__(self, timeout_seconds: int = 300, event_bus=None):
        self._timeout = timeout_seconds
        self._event_bus = event_bus
        self._timer: threading.Timer | None = None
        self._timed_out = threading.Event()

    def start(self, step_name: str):
        """Start the watchdog for a new step.

        Publishes a 'pipeline_progress' event with status 'started'.
        """
        if self._event_bus:
            self._event_bus.publish(
                "pipeline_progress",
                {"step": step_name, "status": "started"},
            )
        self._timer = threading.Timer(self._timeout, self._on_timeout, args=[step_name])
        self._timer.start()

    def reset(self):
        """Reset the watchdog timer for the current step."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def stop(self):
        """Stop the watchdog and clean up."""
        self.reset()

    def _on_timeout(self, step_name: str):
        """Called when the watchdog timer expires."""
        self._timed_out.set()
        if self._event_bus:
            self._event_bus.publish(
                "pipeline_progress",
                {"step": step_name, "status": "timeout"},
            )

    @property
    def timed_out(self) -> bool:
        """Whether the watchdog has triggered a timeout."""
        return self._timed_out.is_set()
