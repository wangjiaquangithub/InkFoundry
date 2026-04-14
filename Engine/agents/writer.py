"""Writer Agent - generates chapter drafts based on Task Cards."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent

if TYPE_CHECKING:
    from Engine.llm.gateway import LLMGateway
    from Engine.llm.prompt_builder import PromptBuilder


class WriterAgent(BaseAgent):
    """Generates narrative drafts based on task cards from the Navigator."""

    def __init__(
        self,
        model_name: str,
        system_prompt: str = "",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
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

    def run(self, task_card: Dict[str, Any]) -> str:
        """Generate a draft for the given chapter task card.

        Args:
            task_card: Contains chapter number, tension level, hooks, etc.

        Returns:
            Draft text for the chapter.
        """
        chapter = task_card.get("chapter", "?")
        tension = task_card.get("tension_level", "normal")
        task_type = task_card.get("type", "development")
        return (
            f"Draft for Chapter {chapter} "
            f"(tension: {tension}, type: {task_type})..."
        )

    async def arun(self, task_card: Dict[str, Any]) -> str:
        """Generate a draft using a real LLM via LLMGateway.

        Args:
            task_card: Contains chapter_num, tension_level, and other metadata.

        Returns:
            Generated chapter content from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(
                f"任务卡: 第{task_card.get('chapter_num', task_card.get('chapter', '?'))}章, "
                f"张力等级: {task_card.get('tension_level', '?')}"
            )
            .with_constraints([
                "生成完整的章节",
                "保持剧情连贯",
                "使用丰富的感官描写",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        content = await gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return content
