"""Writer Agent - generates chapter drafts based on Task Cards."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from Engine.agents.base import BaseAgent
from Engine.config import DEFAULT_LLM_BASE_URL

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

    def run(self, task_card: Dict[str, Any]) -> str:
        """Generate a draft for the given chapter task card.

        Args:
            task_card: Contains chapter number, tension level, hooks, etc.
                       Or kwargs: chapter_num, task_card, chapter_summary.

        Returns:
            Draft text for the chapter.
        """
        if isinstance(task_card, dict) and "chapter_num" in task_card and "task_card" in task_card:
            chapter = task_card.get("chapter_num", "?")
            tc = task_card.get("task_card", {})
            chapter_summary = str(task_card.get("chapter_summary", "") or "")
            historical_context = str(task_card.get("historical_context", "") or "")
            project_brief = task_card.get("project_brief", {})
            tension = tc.get("tension_level", "normal") if isinstance(tc, dict) else "normal"
            task_type = tc.get("type", "development") if isinstance(tc, dict) else "development"
        else:
            chapter = task_card.get("chapter", "?")
            tension = task_card.get("tension_level", "normal")
            task_type = task_card.get("type", "development")
            chapter_summary = ""
            historical_context = ""
            project_brief = {}

        brief_summary = ""
        if isinstance(project_brief, dict):
            brief_summary = str(project_brief.get("summary", "") or "")

        sections = [
            f"Draft for Chapter {chapter} (tension: {tension}, type: {task_type})...",
        ]
        if chapter_summary:
            sections.append(f"Outline: {chapter_summary}")
        if historical_context:
            sections.append(f"History: {historical_context}")
        if brief_summary:
            sections.append(f"Project Brief: {brief_summary}")
        return "\n".join(sections)

    async def arun(self, task_card: Dict[str, Any]) -> str:
        """Generate a draft using a real LLM via LLMGateway.

        Args:
            task_card: Contains chapter_num, tension_level, and other metadata.

        Returns:
            Generated chapter content from the LLM.
        """
        from Engine.llm.prompt_builder import PromptBuilder

        nested_task_card = task_card.get("task_card", {}) if isinstance(task_card, dict) else {}
        chapter_num = task_card.get("chapter_num", task_card.get("chapter", "?"))
        tension_level = (
            nested_task_card.get("tension_level")
            if isinstance(nested_task_card, dict) and nested_task_card.get("tension_level") is not None
            else task_card.get("tension_level", "?")
        )
        task_type = (
            nested_task_card.get("type", "development")
            if isinstance(nested_task_card, dict)
            else task_card.get("type", "development")
        )
        chapter_summary = str(task_card.get("chapter_summary", "") or "")
        historical_context = str(task_card.get("historical_context", "") or "")
        project_brief = task_card.get("project_brief", {})

        project_brief_lines = []
        if isinstance(project_brief, dict):
            title = str(project_brief.get("title", "") or "")
            genre = str(project_brief.get("genre", "") or "")
            summary = str(project_brief.get("summary", "") or "")
            target_chapters = project_brief.get("target_chapters")
            if title:
                project_brief_lines.append(f"标题: {title}")
            if genre:
                project_brief_lines.append(f"题材: {genre}")
            if summary:
                project_brief_lines.append(f"故事简介: {summary}")
            if target_chapters:
                project_brief_lines.append(f"目标章数: {target_chapters}")

        context_parts = [
            f"任务卡: 第{chapter_num}章",
            f"章节类型: {task_type}",
            f"张力等级: {tension_level}",
        ]
        if chapter_summary:
            context_parts.append(f"章节概要:\n{chapter_summary}")
        if historical_context:
            context_parts.append(f"历史上下文:\n{historical_context}")
        if project_brief_lines:
            context_parts.append("项目 Brief:\n" + "\n".join(project_brief_lines))

        builder = (
            PromptBuilder(self.system_prompt)
            .with_context("\n\n".join(context_parts))
            .with_constraints([
                "生成完整的章节",
                "严格遵守章节概要，不要偏离当前章节目标",
                "延续历史上下文中的人物关系、事件因果与世界状态",
                "不要把项目 Brief 当成设定说明重复抄写到正文中",
                "使用丰富但不过度堆砌的感官描写",
            ])
        )
        messages = builder.build()

        gateway = self._get_gateway()
        content = await gateway.chat(messages, temperature=0.8, max_tokens=4096)
        return content
