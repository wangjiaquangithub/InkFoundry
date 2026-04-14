"""Base agent interface for all narrative agents."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from openai import OpenAI


class BaseAgent:
    """Abstract base class for all agents in the narrative pipeline.

    Subclasses must implement the `run` method.
    """

    def __init__(
        self,
        model_name: str,
        system_prompt: str,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.model = model_name
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.base_url = base_url

    @classmethod
    def from_router_info(
        cls,
        router_info: Dict[str, str],
        system_prompt: str,
    ) -> "BaseAgent":
        """Create an agent from a ModelRouter result.

        Args:
            router_info: Dict with 'model', 'api_key', 'base_url' keys.
            system_prompt: The agent's system prompt.

        Returns:
            A configured agent instance.
        """
        return cls(
            model_name=router_info["model"],
            system_prompt=system_prompt,
            api_key=router_info.get("api_key", ""),
            base_url=router_info.get("base_url", "https://api.openai.com/v1"),
        )

    def run(self, context: Dict[str, Any]) -> Any:
        """Execute the agent's primary task.

        Raises:
            NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")

    def _build_client(self) -> OpenAI | None:
        """Build an OpenAI-compatible client.

        Returns:
            OpenAI client instance, or None if openai package is not installed.
        """
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        except ImportError:
            return None
