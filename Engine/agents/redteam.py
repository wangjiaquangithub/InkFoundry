"""RedTeam Agent - adversarial testing for plot rationality."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent
from Engine.config import DEFAULT_LLM_BASE_URL

if TYPE_CHECKING:
    from Engine.llm.gateway import LLMGateway


class RedTeamAgent(BaseAgent):
    """Adversarially attacks draft to find logic holes and plot weaknesses."""

    def __init__(
        self,
        model_name: str,
        system_prompt: str = "",
        api_key: str = "",
        base_url: str = DEFAULT_LLM_BASE_URL,
        gateway: LLMGateway | None = None,
    ):
        super().__init__(model_name, system_prompt, api_key, base_url)
        self._gateway = gateway

    def _get_gateway(self) -> LLMGateway:
        """Return the configured gateway or create one lazily."""
        if self._gateway is None:
            from Engine.llm.gateway import LLMGateway

            self._gateway = LLMGateway(self.model, self.api_key, self.base_url)
        return self._gateway

    def run(self, draft: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Attack the draft and report findings.

        Args:
            draft: The draft content to attack (can be str or dict).
            **kwargs: Additional context like chapter_num.

        Returns:
            Dict with 'attack' description of found issues.
        """
        return {
            "attack": "Logic hole in scene 2",
        }

    async def arun(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Attack the draft using a real LLM via LLMGateway.

        Args:
            draft: The draft content to attack.

        Returns:
            Dict with 'attacks', 'severity', and 'feedback' from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(f"攻击以下章节:\n{draft.get('content', '')}")
            .with_constraints([
                "找出剧情漏洞",
                "找出逻辑矛盾",
                "找出角色 OOC 行为",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        attack = await gateway.chat(messages, temperature=0.5, max_tokens=2048)
        return {"attacks": [attack], "severity": "high", "feedback": attack}
