"""Review Policy Manager — controls when Pipeline interrupts for user review."""
from __future__ import annotations


class ReviewPolicyManager:
    def __init__(self, policy: str = "milestone"):
        self._policy = policy

    def should_interrupt(self, chapter_result: dict) -> bool:
        if self._policy == "strict":
            return True
        elif self._policy == "headless":
            return False
        elif self._policy == "milestone":
            critical = chapter_result.get("critical_issues", [])
            return len(critical) > 0
        return False

    def set_policy(self, policy: str):
        self._policy = policy
