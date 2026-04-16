"""Side story generation agent."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent
from Engine.config import DEFAULT_LLM_BASE_URL

if TYPE_CHECKING:
    from Engine.llm.gateway import LLMGateway

SIDE_STORY_SYSTEM_PROMPT = """你是一个番外故事作家。基于已知的角色和世界设定，创作番外短篇故事。
要求：
- 保持与原故事一致的世界观和角色性格
- 可以探索主线之外的剧情
- 风格可以与原作略有不同
"""


class SideStoryAgent(BaseAgent):
    """Generates side stories (番外) based on existing characters and world settings."""

    SYSTEM_PROMPT = SIDE_STORY_SYSTEM_PROMPT

    def __init__(
        self,
        model_name: str,
        system_prompt: str = "",
        api_key: str = "",
        base_url: str = DEFAULT_LLM_BASE_URL,
        gateway: LLMGateway | None = None,
    ):
        super().__init__(
            model_name,
            system_prompt or self.SYSTEM_PROMPT,
            api_key,
            base_url,
        )
        self._gateway = gateway

    def _get_gateway(self) -> LLMGateway:
        if self._gateway is None:
            from Engine.llm.gateway import LLMGateway
            self._gateway = LLMGateway(self.model, self.api_key, self.base_url)
        return self._gateway

    def run(self, context: Dict[str, Any]) -> str:
        """Generate a side story based on provided context.

        Args:
            context: Contains 'characters' list and 'setting' string.

        Returns:
            Generated side story text.
        """
        characters = context.get("characters", [])
        setting = context.get("setting", "未知")
        return (
            f"番外故事：在{setting}中，"
            f"{', '.join(characters)}展开了一段新的冒险。"
        )

    async def arun(self, context: Dict[str, Any]) -> str:
        """Generate a side story using a real LLM via LLMGateway.

        Args:
            context: Contains 'characters' list, 'setting', and 'topic' strings.

        Returns:
            Generated side story text from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        characters = context.get("characters", [])
        setting = context.get("setting", "")
        topic = context.get("topic", "")

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(
                f"角色: {', '.join(characters)}\n"
                f"世界设定: {setting}\n"
                f"主题: {topic}"
            )
            .with_constraints([
                "保持与原故事一致的世界观",
                "保持角色性格一致",
                "探索主线之外的剧情",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        content = await gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return content
