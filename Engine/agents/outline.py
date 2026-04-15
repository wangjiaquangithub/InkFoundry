"""OutlineAgent — generates novel outlines from prompts."""
from __future__ import annotations

from typing import List, Optional

from Engine.core.models import Outline


class OutlineAgent:
    """Generates novel outlines with story structure.

    Phase 1: Returns a structured template based on genre and chapter count.
    Phase 2+: Will call LLM to generate intelligent outlines.
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

    def run(
        self,
        genre: str = "xuanhuan",
        title: str = "Untitled",
        summary: str = "",
        total_chapters: int = 100,
    ) -> Outline:
        """Generate an outline for the novel.

        Args:
            genre: Novel genre (xuanhuan, xianxia, urban, scifi, wuxia).
            title: Novel title.
            summary: One-line story summary.
            total_chapters: Target chapter count.

        Returns:
            Outline with story structure.
        """
        per_volume = max(1, total_chapters // 4)

        # Generate chapter summaries
        chapter_summaries = self._generate_chapter_summaries(
            total_chapters, per_volume
        )

        # Generate tension curve
        tension_curve = [c["tension"] for c in chapter_summaries]

        # Generate volume plans
        volume_plans = self._generate_volume_plans(
            total_chapters, per_volume
        )

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

    def _generate_chapter_summaries(
        self, total_chapters: int, per_volume: int
    ) -> List[dict]:
        """Generate one-line summaries for each chapter."""
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

    def _generate_volume_plans(
        self, total_chapters: int, per_volume: int
    ) -> List[dict]:
        """Generate volume plan definitions."""
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
