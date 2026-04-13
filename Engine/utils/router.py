"""Hierarchical Model Router - routes tasks to different LLMs."""
from __future__ import annotations

from typing import Any, Dict


class ModelRouter:
    """Routes tasks to appropriate LLMs based on agent type and importance.

    Hierarchy:
    - L1: Global default model
    - L2: Agent-specific overrides
    - L3: Task-level overrides (e.g., climax chapters use higher-tier model)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_model(self, agent_type: str, importance: str = "low") -> str:
        """Determine the model to use for a task.

        Args:
            agent_type: The type of agent (writer, editor, etc.).
            importance: Task importance level ('low', 'high').

        Returns:
            Model name string.
        """
        if agent_type == "writer" and importance == "high":
            return self.config.get("climax_model", "gpt-4o")
        return self.config.get("default_model", "qwen-plus")
