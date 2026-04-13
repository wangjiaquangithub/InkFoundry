"""Navigator Agent - generates task cards with tension heatmap tracking."""
from __future__ import annotations

from typing import Any, Dict, List

from Engine.agents.base import BaseAgent


class NavigatorAgent(BaseAgent):
    """Tracks pacing via tension levels and generates chapter task cards.

    Forces high-tension chapters when recent history has been too calm.
    """

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run navigator logic - generate task card.

        Args:
            context: Should contain chapter_num and history_tension.
        """
        chapter = context.get("chapter_num", 1)
        history = context.get("history_tension", [])
        return self.generate_task_card(chapter, history)

    def generate_task_card(
        self, chapter_num: int, history_tension: List[int]
    ) -> Dict[str, Any]:
        """Generate a task card for the given chapter.

        If the last 3 chapters had low total tension (<15), force a high-tension chapter.

        Args:
            chapter_num: The chapter to generate a card for.
            history_tension: Tension levels of previous chapters.

        Returns:
            Task card dict with chapter, tension_level, and type.
        """
        if len(history_tension) >= 3 and sum(history_tension[-3:]) < 15:
            tension = 9
            task_type = "high_conflict"
        else:
            tension = 4
            task_type = "development"

        return {
            "chapter": chapter_num,
            "tension_level": tension,
            "type": task_type,
        }
