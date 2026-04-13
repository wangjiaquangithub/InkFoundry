"""Writer Agent - generates chapter drafts based on Task Cards."""
from __future__ import annotations

from typing import Any, Dict

from Engine.agents.base import BaseAgent


class WriterAgent(BaseAgent):
    """Generates narrative drafts based on task cards from the Navigator."""

    def run(self, task_card: Dict[str, Any]) -> str:
        """Generate a draft for the given chapter task card.

        Args:
            task_card: Contains chapter number, tension level, hooks, etc.

        Returns:
            Draft text for the chapter.
        """
        chapter = task_card.get("chapter", "?")
        tension = task_card.get("tension_level", "normal")
        task_type = task_card.get("type", "development")
        return (
            f"Draft for Chapter {chapter} "
            f"(tension: {tension}, type: {task_type})..."
        )
