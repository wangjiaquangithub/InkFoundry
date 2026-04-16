"""PipelineOrchestrator — chains all agents into a novel-writing pipeline."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from Engine.core.state_db import StateDB
from Engine.core.event_bus import EventBus, get_event_bus
from Engine.core.models import Chapter


class PipelineOrchestrator:
    """Orchestrates the full novel-writing pipeline.

    Chains: Navigator → MemoryBank recall → StateFilter → Writer → Editor → RedTeam → Save

    Args:
        state_db: StateDB instance for persistence.
        event_bus: Optional EventBus for real-time events.
        config: Optional EngineConfig for real LLM calls.
        memory_bank: Optional MemoryBank for historical context recall.
        review_policy: Review policy mode: "strict", "milestone", or "headless".
    """

    def __init__(
        self,
        state_db: StateDB,
        event_bus: Optional[EventBus] = None,
        config: Optional[Any] = None,
        memory_bank: Optional[Any] = None,
        review_policy: str = "strict",
    ):
        self.state_db = state_db
        self.event_bus = event_bus if event_bus is not None else get_event_bus()
        self.config = config  # EngineConfig or None
        self.memory_bank = memory_bank  # MemoryBank or None
        self.review_policy = review_policy
        self._running = False
        self._paused = False
        self._current_chapter = 0
        self._total_chapters = 0

    def _publish(self, event_type: str, data: dict) -> None:
        """Publish event to EventBus."""
        if self.event_bus:
            self.event_bus.publish(event_type, data)

    async def run_chapter(self, chapter_num: int) -> Dict[str, Any]:
        """Execute the full pipeline for a single chapter.

        1. Read outline for chapter context
        2. Navigator generates TaskCard
        3. Writer generates draft (real LLM if configured)
        4. Editor reviews (real LLM if configured)
        5. RedTeam attacks (real LLM if configured)
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

            # Step 2: Navigator generates TaskCard (pure rules, no LLM)
            from Engine.agents.navigator import NavigatorAgent
            navigator = NavigatorAgent(model_name="dummy", system_prompt="")
            task_card = navigator.run({
                "chapter_num": chapter_num,
                "total_chapters": total_chapters,
                "chapter_summary": chapter_summary,
                "outline": outline,
            })

            # Step 2.5: Recall historical context from MemoryBank + StateFilter
            historical_context = ""
            if self.memory_bank:
                # Retrieve recent chapters for continuity context
                recent_memories = self.memory_bank.query(
                    f"chapter {chapter_num} plot summary",
                    n_results=5,
                )
                if recent_memories:
                    # Filter through StateFilter to remove dead/inactive characters
                    from Engine.core.filter import StateFilter
                    state_filter = StateFilter(state_db=self.state_db)

                    # Convert to dict format for filtering
                    rag_context = {}
                    for i, memory in enumerate(recent_memories):
                        rag_context[f"memory_{i}"] = memory

                    filtered = state_filter.apply(rag_context)
                    historical_context = "\n".join(filtered.values())

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "writer",
                "agent": "writer",
                "status": "running",
                "progress": 0.3,
            })

            # Step 3: Writer generates draft
            from Engine.agents.writer import WriterAgent
            draft = await self._run_writer(
                chapter_num=chapter_num,
                task_card=task_card,
                chapter_summary=chapter_summary,
                historical_context=historical_context,
            )

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "editor",
                "agent": "editor",
                "status": "running",
                "progress": 0.5,
            })

            # Step 4: Editor reviews
            from Engine.agents.editor import EditorAgent
            review = await self._run_editor(draft=draft, chapter_num=chapter_num)

            self._publish("pipeline_progress", {
                "chapter": chapter_num,
                "step": "redteam",
                "agent": "redteam",
                "status": "running",
                "progress": 0.7,
            })

            # Step 5: RedTeam attacks
            from Engine.agents.redteam import RedTeamAgent
            attack = await self._run_redteam(draft=draft, chapter_num=chapter_num)

            # Step 5.5: ReviewPolicy determines chapter status
            from Engine.core.review_policy import ReviewPolicyManager
            policy_manager = ReviewPolicyManager(policy=self.review_policy)

            # Combine results for policy evaluation
            combined_result = {
                "score": review.get("score", 80) if isinstance(review, dict) else 80,
                "critical_issues": [],
            }
            # Extract critical issues from review and attack
            if isinstance(review, dict):
                issues = review.get("issues", [])
                for issue in issues:
                    if isinstance(issue, dict) and issue.get("severity") == "critical":
                        combined_result["critical_issues"].append(issue)
                    elif isinstance(issue, str) and "critical" in issue.lower():
                        combined_result["critical_issues"].append(issue)

            if isinstance(attack, dict):
                severity = attack.get("severity", "")
                if severity == "high":
                    combined_result["critical_issues"].append(attack.get("feedback", ""))

            should_interrupt = policy_manager.should_interrupt(combined_result)
            score = combined_result["score"]

            if self.review_policy == "headless":
                status = "final"  # Auto-approve in headless mode
            elif should_interrupt:
                status = "reviewed"  # Needs user approval
            else:
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

            # Store chapter summary in MemoryBank for future recall
            if self.memory_bank:
                summary = draft[:500]  # First 500 chars as summary
                self.memory_bank.add_summary(chapter_num, summary)

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

    def _has_api_key(self) -> bool:
        """Check if a real API key is configured."""
        if self.config is None:
            return False
        try:
            from Engine.config import EngineConfig
            if isinstance(self.config, EngineConfig):
                return bool(self.config.llm.api_key)
        except Exception:
            pass
        return False

    async def _run_writer(
        self, chapter_num: int, task_card: dict, chapter_summary: str,
        historical_context: str = "",
    ) -> str:
        """Run WriterAgent — real LLM if configured, fallback to mock."""
        from Engine.agents.writer import WriterAgent

        # Build system prompt with optional voice injection
        system_prompt = "你是专业的小说作家，擅长长篇小说创作。"
        system_prompt = self._inject_voice(system_prompt)

        if self._has_api_key():
            model_name = self.config.role_models.get("writer", self.config.llm.default_model)
            writer = WriterAgent(
                model_name=model_name,
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url,
                system_prompt=system_prompt,
            )
            return await asyncio.wait_for(
                writer.arun({
                    "chapter_num": chapter_num,
                    "task_card": task_card,
                    "chapter_summary": chapter_summary,
                    "historical_context": historical_context,
                }),
                timeout=120,
            )

        # Fallback: mock
        writer = WriterAgent(model_name="dummy", system_prompt=system_prompt)
        return writer.run({
            "chapter_num": chapter_num,
            "task_card": task_card,
            "chapter_summary": chapter_summary,
        })

    def _inject_voice(self, system_prompt: str) -> str:
        """Inject voice constraints from character profiles with voice_profile_ref.

        Reads all character profiles from StateDB. If any have a non-default
        voice_profile_ref, loads the corresponding voice config and injects
        it via VoiceSandbox.
        """
        try:
            profiles = self.state_db.list_character_profiles()
            voice_refs = [
                p.voice_profile_ref for p in profiles
                if p.voice_profile_ref and p.voice_profile_ref != "default"
            ]
            if not voice_refs:
                return system_prompt

            from Engine.agents.voice_sandbox import VoiceSandbox
            import os
            voices_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "voices")

            # Use the first non-default voice profile found
            voice_file = os.path.join(voices_dir, f"{voice_refs[0]}.yaml")
            if os.path.exists(voice_file):
                sandbox = VoiceSandbox(config_path=voice_file)
                return sandbox.inject_prompt(system_prompt)
        except Exception:
            pass  # Silently skip voice injection on error

        return system_prompt

    async def _run_editor(self, draft: str, chapter_num: int) -> Dict[str, Any]:
        """Run EditorAgent — real LLM if configured, fallback to mock."""
        from Engine.agents.editor import EditorAgent

        if self._has_api_key():
            model_name = self.config.role_models.get("editor", self.config.llm.default_model)
            editor = EditorAgent(
                model_name=model_name,
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url,
                system_prompt="你是专业的小说编辑，擅长检查逻辑一致性和文风。",
            )
            return await asyncio.wait_for(
                editor.arun({"content": draft, "chapter_num": chapter_num}),
                timeout=60,
            )

        # Fallback: mock
        editor = EditorAgent(model_name="dummy", system_prompt="")
        return editor.run(draft=draft, chapter_num=chapter_num)

    async def _run_redteam(self, draft: str, chapter_num: int) -> Dict[str, Any]:
        """Run RedTeamAgent — real LLM if configured, fallback to mock."""
        from Engine.agents.redteam import RedTeamAgent

        if self._has_api_key():
            model_name = self.config.role_models.get("redteam", self.config.llm.default_model)
            redteam = RedTeamAgent(
                model_name=model_name,
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url,
                system_prompt="你是 adversarial reviewer，专门找剧情漏洞和逻辑矛盾。",
            )
            return await asyncio.wait_for(
                redteam.arun({"content": draft, "chapter_num": chapter_num}),
                timeout=60,
            )

        # Fallback: mock
        redteam = RedTeamAgent(model_name="dummy", system_prompt="")
        return redteam.run(draft=draft, chapter_num=chapter_num)

    async def run_batch(self, start: int, end: int) -> Dict[str, Any]:
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
                results[ch_num] = await self.run_chapter(ch_num)
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
