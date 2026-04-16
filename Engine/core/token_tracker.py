"""LLM token usage tracking and statistics with StateDB persistence."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from Engine.core.state_db import StateDB


@dataclass
class TokenRecord:
    timestamp: float
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    task: str = ""  # e.g., "writer_chapter_1", "editor_review"

    @property
    def cost_estimate(self) -> float:
        """Estimate cost in USD (based on common model pricing)."""
        if "opus" in self.model:
            return (self.prompt_tokens * 0.015 + self.completion_tokens * 0.075) / 1_000_000
        elif "sonnet" in self.model:
            return (self.prompt_tokens * 0.003 + self.completion_tokens * 0.015) / 1_000_000
        else:
            return (self.prompt_tokens * 0.001 + self.completion_tokens * 0.002) / 1_000_000


@dataclass
class TokenStats:
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_requests: int = 0
    total_cost_estimate: float = 0.0
    by_model: dict[str, int] = field(default_factory=dict)
    by_task: dict[str, int] = field(default_factory=dict)


class TokenTracker:
    """Token tracker that persists records to StateDB."""

    _TOKEN_KEY = "token_records"

    def __init__(self, state_db: Optional[StateDB] = None):
        self._state_db = state_db
        self._stats = TokenStats()
        # Load existing records from StateDB
        self._records: list[TokenRecord] = []
        if self._state_db:
            self._load_records()

    def _load_records(self) -> None:
        """Load token records from StateDB."""
        try:
            data = self._state_db.get_state(self._TOKEN_KEY)
            if data and "records" in data:
                self._records = [
                    TokenRecord(**r) for r in data["records"]
                ]
                for r in self._records:
                    self._update_stats(r)
        except Exception:
            pass

    def _save_records(self) -> None:
        """Save all token records to StateDB."""
        if not self._state_db:
            return
        try:
            self._state_db.update_state(
                self._TOKEN_KEY,
                {"records": [
                    {
                        "timestamp": r.timestamp,
                        "model": r.model,
                        "prompt_tokens": r.prompt_tokens,
                        "completion_tokens": r.completion_tokens,
                        "total_tokens": r.total_tokens,
                        "task": r.task,
                    }
                    for r in self._records
                ]},
            )
        except Exception:
            pass  # Don't fail on tracking errors

    def record(self, model: str, prompt_tokens: int, completion_tokens: int, task: str = ""):
        record = TokenRecord(
            timestamp=time.time(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            task=task,
        )
        self._records.append(record)
        self._update_stats(record)
        self._save_records()

    def _update_stats(self, record: TokenRecord):
        self._stats.total_prompt_tokens += record.prompt_tokens
        self._stats.total_completion_tokens += record.completion_tokens
        self._stats.total_tokens += record.total_tokens
        self._stats.total_requests += 1
        self._stats.total_cost_estimate += record.cost_estimate

        self._stats.by_model[record.model] = self._stats.by_model.get(record.model, 0) + record.total_tokens
        if record.task:
            self._stats.by_task[record.task] = self._stats.by_task.get(record.task, 0) + record.total_tokens

    @property
    def stats(self) -> TokenStats:
        return self._stats

    @property
    def records(self) -> list[TokenRecord]:
        return list(self._records)

    def reset(self):
        self._records = []
        self._stats = TokenStats()
        if self._state_db:
            self._state_db.update_state(self._TOKEN_KEY, {"records": []})

    def get_stats_by_model(self) -> dict[str, int]:
        return dict(self._stats.by_model)

    def get_stats_by_task(self) -> dict[str, int]:
        return dict(self._stats.by_task)
