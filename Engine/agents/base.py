"""Base agent interface for all narrative agents."""
from __future__ import annotations

from typing import Any, Dict


class BaseAgent:
    """Abstract base class for all agents in the narrative pipeline.

    Subclasses must implement the `run` method.
    """

    def __init__(self, model_name: str, system_prompt: str):
        self.model = model_name
        self.system_prompt = system_prompt

    def run(self, context: Dict[str, Any]) -> Any:
        """Execute the agent's primary task.

        Raises:
            NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")
