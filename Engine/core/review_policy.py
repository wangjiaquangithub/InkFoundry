"""Review Policy Manager — controls when Pipeline interrupts for user review."""
from __future__ import annotations


class ReviewPolicyManager:
    """Manages review workflow modes.

    Three modes:
    - strict: Every chapter needs user approval (interrupt always)
    - milestone: Only interrupt on critical issues
    - headless: Fire-and-forget, auto-approve everything
    """

    def __init__(self, policy: str = "strict"):
        self._policy = policy

    def should_interrupt(self, chapter_result: dict) -> bool:
        """Check if the pipeline should interrupt for user review."""
        if self._policy == "strict":
            return True
        elif self._policy == "headless":
            return False
        elif self._policy == "milestone":
            critical = chapter_result.get("critical_issues", [])
            return len(critical) > 0
        return False

    def decide_status(self, score: int) -> str:
        """Decide chapter status based on policy.

        Returns:
            "final" for headless mode (auto-approved)
            "reviewed" for strict/milestone (needs user approval)
        """
        if self._policy == "headless":
            return "final"
        return "reviewed"

    def set_policy(self, policy: str):
        self._policy = policy
