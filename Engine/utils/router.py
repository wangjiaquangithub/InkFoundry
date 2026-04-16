"""Hierarchical Model Router - routes tasks to different LLMs."""
from __future__ import annotations

from typing import Any, Dict, TypedDict

from Engine.config import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL


class ModelInfo(TypedDict):
    """Resolved model configuration."""
    model: str
    api_key: str
    base_url: str


class ModelRouter:
    """Routes tasks to appropriate LLMs based on agent type and importance.

    Hierarchy:
    - L1: Global default model
    - L2: Agent-specific overrides (writer, editor, redteam, navigator, director)
    - L3: Task-level overrides (e.g., climax chapters use higher-tier model)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_model(
        self, agent_type: str, importance: str = "low"
    ) -> ModelInfo:
        """Determine the model to use for a task.

        Args:
            agent_type: The type of agent (writer, editor, etc.).
            importance: Task importance level ('low', 'high').

        Returns:
            ModelInfo dict with model name, api_key, and base_url.
        """
        # Determine model name
        if agent_type == "writer" and importance == "high":
            # L3: Writer with high importance gets role-specific model
            model_name = self.config.get("writer", self.config.get("default_model", DEFAULT_LLM_MODEL))
        elif agent_type in ("editor", "redteam", "navigator", "director") and agent_type in self.config:
            # L2: Agent-specific override for non-writer roles
            model_name = self.config[agent_type]
        else:
            # L1: Global default (writer low importance also goes here)
            model_name = self.config.get("default_model", DEFAULT_LLM_MODEL)

        return ModelInfo(
            model=model_name,
            api_key=self.config.get("api_key", ""),
            base_url=self.config.get("base_url", DEFAULT_LLM_BASE_URL),
        )
