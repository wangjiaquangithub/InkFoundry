"""PipelineOrchestrator — chains all agents into a novel-writing pipeline."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from Engine.core.state_db import StateDB
from Engine.core.event_bus import EventBus, get_event_bus
from Engine.core.models import Chapter


class PipelineOrchestrator:
    """Orchestrates the full novel-writing pipeline.

    Chains: Navigator → Writer → Editor → RedTeam → Save

    Args:
        state_db: StateDB instance for persistence.
        event_bus: Optional EventBus for real-time events.
    """

    def __init__(self, state_db: StateDB, event_bus: Optional[EventBus] = None):
        self.state_db = state_db
        self.event_bus = event_bus if event_bus is not None else get_event_bus()
        self._running = False
        self._paused = False
        self._current_chapter = 0
        self._total_chapters = 0

    def _publish(self, event_type: str, data: dict) -> None:
        """Publish event to EventBus."""
        if self.event_bus:
            self.event_bus.publish(event_type, data)

    def run_chapter(self, chapter_num: int) -> Dict[str, Any]:
        """Execute the full pipeline for a single chapter.

        1. Read outline for chapter context
        2. Navigator generates TaskCard
        3. Writer generates draft
        4. Editor reviews
        5. RedTeam attacks
        6. Save chapter to StateDB

        Args:
            chapter_num: Chapter number to write.

        Returns:
            Chapter result dict.
        """
        self._running = True
        self._current_chapter = chapter_num
        start_time = time.time()

        self._publish("pipeline_progress", {
            "chapter": chapter_num,
            "step": "starting",
            "status": "running",
        })

        try:
            # Step 1: Get outline context
            outline = self.state_db.get_outline()
            chapter_summary = ""
            total_chapters = outline.total_chapters if outline else 100
            if outline and chapter_num <= len(outline.chapter_summaries):
                ch_info = outline.chapter_summaries[chapter_num - 1]
                chapter_summary = ch_info.get("summary", f"Chapter {chapter_num}")

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "navigator",
                "agent": "navigator",
                "status": "running",
                "progress": 0.1,
            })

            # Step 2: Navigator generates TaskCard
            from Engine.agents.navigator import NavigatorAgent
            navigator = NavigatorAgent(model_name="dummy", system_prompt="")
            task_card = navigator.run({
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "chapter_summary": chapter_summary,
                "outline": outline,
            })

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "writer",
                "agent": "writer",
                "status": "running",
                "progress": 0.3,
            })

            # Step 3: Writer generates draft
            from Engine.agents.writer import WriterAgent
            writer = WriterAgent(model_name="dummy", system_prompt="")
            draft = writer.run({
                "chapter_num": chapter_num,
                "task_card": task_card,
                "chapter_summary": chapter_summary,
            })

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "editor",
                "agent": "editor",
                "status": "running",
                "progress": 0.5,
            })

            # Step 4: Editor reviews
            from Engine.agents.editor import EditorAgent
            editor = EditorAgent(model_name="dummy", system_prompt="")
            review = editor.run(draft=draft, chapter_num=chapter_num)

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "redteam",
                "agent": "redteam",
                "status": "running",
                "progress": 0.7,
            })

            # Step 5: RedTeam attacks
            from Engine.agents.redteam import RedTeamAgent
            redteam = RedTeamAgent(model_name="dummy", system_prompt="")
            attack = redteam.run(draft=draft, chapter_num=chapter_num)

            # Combine results
            score = review.get("score", 80) if isinstance(review, dict) else 80
            status = "reviewed" if score >= 70 else "draft"

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "saving",
                "status": "running",
                "progress": 0.9,
            })

            # Step 6: Save chapter
            chapter = Chapter(
                chapter_num=chapter_num,
                title=f"Chapter {chapter_num}",
                content=draft,
                status=status,
                word_count=len(draft),
                tension_level=task_card.get("tension_level", 5) if isinstance(task_card, dict) else 5,
                review_notes=f"Editor score: {score}. RedTeam: {attack}",
                agent_results={
                    "navigator": task_card,
                    "editor": review,
                    "redteam": attack,
                },
            )
            self.state_db.update_chapter(chapter)

            elapsed = time.time() - start_time
            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "complete",
                "status": "done",
                "progress": 1.0,
                "score": score,
                "elapsed": elapsed,
            })
            self._publish("chapter_complete", {
                "chapter_num": chapter_num,
                "score": score,
                "status": status,
            })

            return {
                "chapter_num": chapter_num,
                "status": status,
                "score": score,
                "content": draft,
                "elapsed": elapsed,
            }

        except Exception as e:
            self._publish("chapter_failed", {
                "chapter_num": chapter_num,
                "error": str(e),
            })
            raise
        finally:
            self._running = False

    def run_batch(self, start: int, end: int) -> Dict[str, Any]:
        """Run the pipeline for a batch of chapters.

        Args:
            start: Starting chapter number.
            end: Ending chapter number (inclusive).

        Returns:
            Summary dict with results per chapter.
        """
        self._total_chapters = end - start + 1
        results = {}
        for ch_num in range(start, end + 1):
            if self._paused:
                results[ch_num] = {"status": "paused"}
                continue
            try:
                results[ch_num] = self.run_chapter(ch_num)
            except Exception as e:
                results[ch_num] = {"status": "failed", "error": str(e)}
        self._publish("batch_complete", {
            "start": start,
            "end": end,
            "results": results,
        })
        return results

    def pause(self) -> None:
        """Pause the pipeline."""
        self._paused = True
        self._publish("pipeline_progress", {"step": "pause", "status": "paused"})

    def resume(self) -> None:
        """Resume the pipeline."""
        self._paused = False
        self._publish("pipeline_progress", {"step": "resume", "status": "running"})

    def stop(self) -> None:
        """Stop the pipeline."""
        self._running = False
        self._paused = False
        self._publish("pipeline_progress", {"step": "stop", "status": "stopped"})

    @property
    def status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "running": self._running,
            "paused": self._paused,
            "current_chapter": self._current_chapter,
            "total_chapters": self._total_chapters,
        }
