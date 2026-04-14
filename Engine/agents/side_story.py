"""Side story generation agent."""
from __future__ import annotations

from typing import Any, Dict

from Engine.agents.base import BaseAgent


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
        base_url: str = "https://api.openai.com/v1",
    ):
        super().__init__(
            model_name,
            system_prompt or self.SYSTEM_PROMPT,
            api_key,
            base_url,
        )

    async def run(self, context: Dict[str, Any]) -> str:
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
