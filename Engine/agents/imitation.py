"""Style imitation agent — writes in the style of provided text."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent
from Engine.config import DEFAULT_LLM_BASE_URL

if TYPE_CHECKING:
    from Engine.llm.gateway import LLMGateway


IMITATION_SYSTEM_PROMPT = """你是一个模仿写作的高手。分析提供的样本文本的风格特征，并用同样的风格创作新内容。
要求：
- 分析样本的句式、节奏、用词特点
- 在新内容中复现这些风格特征
- 保持剧情的连贯性
"""


class ImitationAgent(BaseAgent):
    """Writes content imitating the style of a provided sample text."""

    SYSTEM_PROMPT = IMITATION_SYSTEM_PROMPT

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
        """Generate content imitating the style of a sample.

        Args:
            context: Contains 'sample_text' and 'topic' strings.

        Returns:
            Generated text in the style of the sample.
        """
        sample = context.get("sample_text", "")
        topic = context.get("topic", "")
        return (
            f"模仿样本风格写作：关于「{topic}」的内容，"
            f"使用与样本相同的写作风格。"
        )

    async def arun(self, context: Dict[str, Any]) -> str:
        """Generate imitation content using a real LLM via LLMGateway.

        Args:
            context: Contains 'sample_text' and 'topic' strings.

        Returns:
            Generated text in the style of the sample from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        sample = context.get("sample_text", "")
        topic = context.get("topic", "")

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context(
                f"样本文本: {sample[:500]}\n"
                f"写作主题: {topic}"
            )
            .with_constraints([
                "分析样本的句式特点",
                "分析样本的节奏和用词",
                "在新内容中复现这些风格特征",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        content = await gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return content
