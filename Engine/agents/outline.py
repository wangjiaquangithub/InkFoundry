"""OutlineAgent — generates novel outlines from prompts."""
from __future__ import annotations

import json
from typing import List, Optional

from Engine.core.models import Outline


class OutlineAgent:
    """Generates novel outlines with story structure.

    Phase 1: Returns a structured template based on genre and chapter count.
    Phase 2: Calls LLM to generate intelligent outlines when API key is configured.
    """

    # Genre-specific writing rules
    GENRE_RULES = {
        "xuanhuan": ["战力不能倒退", "每章至少一场战斗或修炼描写"],
        "xianxia": ["修炼等级递进", "天道规则不可违"],
        "urban": ["现实逻辑", "使用2026年法律术语"],
        "scifi": ["科技自洽", "物理定律遵守"],
        "wuxia": ["武功招式描写", "江湖规矩"],
    }

    # Four-act structure names
    ARC_PHASES = ["起", "承", "转", "合"]

    def __init__(
        self,
        model_name: str = "qwen-plus",
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url

    def _has_api_key(self) -> bool:
        return bool(self.api_key)

    async def arun(
        self,
        genre: str = "xuanhuan",
        title: str = "Untitled",
        summary: str = "",
        total_chapters: int = 100,
    ) -> Outline:
        """Generate an outline using LLM.

        Args:
            genre: Novel genre.
            title: Novel title.
            summary: One-line story summary.
            total_chapters: Target chapter count.

        Returns:
            Outline with LLM-generated structure.
        """
        from Engine.llm.gateway import LLMGateway
        from Engine.llm.prompt_builder import PromptBuilder

        system_prompt = (
            "你是一个专业的小说大纲策划师，擅长为长篇小说设计完整的故事结构。"
            "请根据给定的题材、标题和简介，生成包含分卷计划、章节概要和张力曲线的详细大纲。"
        )

        builder = (
            PromptBuilder(system_prompt)
            .with_context(
                f"题材: {genre}\n"
                f"标题: {title}\n"
                f"简介: {summary}\n"
                f"总章节数: {total_chapters}章\n\n"
                f"请按照起承转合四段式结构设计大纲，"
                f"为每章生成一句话概要(20字以内)和张力等级(1-10)。"
                f"返回 JSON 格式:\n"
                f"{{\"chapter_summaries\": [{{"
                f"\"chapter_num\": 1, \"summary\": \"...\", \"tension\": 5"
                f"}}], \"foreshadowing\": [\"伏笔1\", \"伏笔2\"]}}"
            )
            .with_constraints([
                "遵守起承转合的故事结构",
                f"题材为 {genre}，需包含该题材的核心元素",
                "张力等级从低到高再回落",
                "章节概要要连贯，前后有因果关联",
                "只返回 JSON，不要其他解释",
            ])
        )
        messages = builder.build()

        gateway = LLMGateway(self.model_name, self.api_key, self.base_url)
        content = await gateway.chat(messages, temperature=0.7, max_tokens=4096)

        # Parse JSON response
        try:
            # Extract JSON from possible markdown code blocks
            json_str = content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[-1]
            if json_str.endswith("```"):
                json_str = json_str.rsplit("\n", 1)[0]
            json_str = json_str.strip()
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()

            llm_data = json.loads(json_str)
            chapter_summaries = llm_data.get("chapter_summaries", [])
            foreshadowing = llm_data.get("foreshadowing", [])
        except (json.JSONDecodeError, KeyError):
            # Fallback to template if JSON parsing fails
            return self.run(genre=genre, title=title, summary=summary, total_chapters=total_chapters)

        # Build tension curve
        tension_curve = [c.get("tension", 5) for c in chapter_summaries]

        # Generate volume plans
        volume_plans = self._generate_volume_plans(total_chapters)

        return Outline(
            title=title,
            summary=summary,
            total_chapters=total_chapters,
            arc="hero_journey",
            volume_plans=volume_plans,
            chapter_summaries=chapter_summaries,
            tension_curve=tension_curve,
            foreshadowing=foreshadowing,
            genre_rules=self.GENRE_RULES.get(genre, []),
        )

    def run(
        self,
        genre: str = "xuanhuan",
        title: str = "Untitled",
        summary: str = "",
        total_chapters: int = 100,
    ) -> Outline:
        """Generate an outline using template-based approach (fallback).

        Args:
            genre: Novel genre (xuanhuan, xianxia, urban, scifi, wuxia).
            title: Novel title.
            summary: One-line story summary.
            total_chapters: Target chapter count.

        Returns:
            Outline with story structure.
        """
        # Generate chapter summaries
        chapter_summaries = self._generate_chapter_summaries(
            total_chapters
        )

        # Generate tension curve
        tension_curve = [c["tension"] for c in chapter_summaries]

        # Generate volume plans
        volume_plans = self._generate_volume_plans(total_chapters)

        return Outline(
            title=title,
            summary=summary,
            total_chapters=total_chapters,
            arc="hero_journey",
            volume_plans=volume_plans,
            chapter_summaries=chapter_summaries,
            tension_curve=tension_curve,
            foreshadowing=[],
            genre_rules=self.GENRE_RULES.get(genre, []),
        )

    def _generate_chapter_summaries(self, total_chapters: int) -> List[dict]:
        """Generate one-line summaries for each chapter."""
        per_volume = max(1, total_chapters // 4)
        summaries = []
        chapter_num = 1
        for phase_idx in range(4):
            # Last phase gets all remaining chapters
            if phase_idx == 3:
                phase_end = total_chapters
            else:
                phase_end = min((phase_idx + 1) * per_volume, total_chapters)
            for ch in range(chapter_num, phase_end + 1):
                summaries.append({
                    "chapter_num": ch,
                    "summary": f"第{ch}章 — {self.ARC_PHASES[phase_idx]}阶段",
                    "tension": 3 + phase_idx * 2,
                })
            chapter_num = phase_end + 1
            if chapter_num > total_chapters:
                break
        return summaries[:total_chapters]

    def _generate_volume_plans(self, total_chapters: int) -> List[dict]:
        """Generate volume plan definitions."""
        per_volume = max(1, total_chapters // 4)
        plans = []
        vol_start = 1
        for i in range(4):
            if i == 3:
                vol_end = total_chapters
            else:
                vol_end = min((i + 1) * per_volume, total_chapters)
            plans.append({
                "volume": i + 1,
                "name": f"第{self.ARC_PHASES[i]}卷",
                "chapters": f"{vol_start}-{vol_end}",
            })
            vol_start = vol_end + 1
            if vol_start > total_chapters:
                break
        return plans
