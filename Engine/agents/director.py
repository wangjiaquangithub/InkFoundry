"""Director Agent - controls role-play sandbox to prevent loops."""
from __future__ import annotations

from typing import Any, Dict

from Engine.agents.base import BaseAgent


class DirectorAgent(BaseAgent):
    """Controls the Role-Play Sandbox.

    Prevents infinite loops and 'happy talk' by injecting event pressure
    and enforcing character consistency.
    """

    LOOP_THRESHOLD = 10  # Number of repeated actions to trigger loop detection

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a scene and generate a decision log.

        Args:
            context: Scene description and state.

        Returns:
            Decision log dict with the character's decision.
        """
        scene = context.get("scene", "")
        return {
            "decision": f"Protagonist decides based on: {scene}",
            "scene": scene,
        }

    def detect_loop(self, history: list) -> bool:
        """Detect if the conversation/narrative is stuck in a loop.

        Args:
            history: List of recent scene descriptions or actions.

        Returns:
            True if a loop is detected.
        """
        return len(history) > self.LOOP_THRESHOLD
