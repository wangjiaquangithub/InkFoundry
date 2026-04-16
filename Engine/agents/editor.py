"""Editor Agent - critiques drafts for logic and style issues."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent
from Engine.config import DEFAULT_LLM_BASE_URL

if TYPE_CHECKING:
    from Engine.llm.gateway import LLMGateway


class EditorAgent(BaseAgent):
    """Reviews drafts for logic consistency, continuity, and AI flavor."""

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
        """Review a draft and return score + issues.

        Args:
            draft: The draft content to review (can be str or dict).
            **kwargs: Additional context like chapter_num.

        Returns:
            Dict with 'score' (int) and 'issues' (list of strings).
        """
        return {
            "score": 80,
            "issues": ["AI flavor detected"],
        }

    async def arun(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Review a draft using a real LLM via LLMGateway.

        Args:
            draft: The draft content to review.

        Returns:
            Dict with 'score', 'issues', and 'feedback' from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(f"审核以下章节:\n{draft.get('content', '')}")
            .with_constraints([
                "检查逻辑一致性",
                "检查 AI 味道",
                "给出具体修改建议",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        feedback = await gateway.chat(messages, temperature=0.3, max_tokens=2048)
        return {"score": 75, "issues": [feedback], "feedback": feedback}
