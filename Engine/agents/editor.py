"""Editor Agent - critiques drafts for logic and style issues."""
from __future__ import annotations

from typing import Any, Dict

from Engine.agents.base import BaseAgent


class EditorAgent(BaseAgent):
    """Reviews drafts for logic consistency, continuity, and AI flavor."""

    def run(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Review a draft and return score + issues.

        Args:
            draft: The draft content to review.

        Returns:
            Dict with 'score' (int) and 'issues' (list of strings).
        """
        return {
            "score": 80,
            "issues": ["AI flavor detected"],
        }
