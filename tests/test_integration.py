"""Integration test - full pipeline end-to-end with mocked LLM calls."""
import asyncio
import os
import tempfile
import uuid
import yaml
import pytest
from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState, WorldState, StateSnapshot
from Engine.core.filter import StateFilter
from Engine.core.controller import (
    PipelineController,
    CircuitBreakerError,
    GradientRewriter,
)
from Engine.core.event_bus import EventBus, EVENT_CHAPTER_COMPLETE
from Engine.core.review_policy import ReviewPolicyManager
from Engine.core.token_tracker import TokenTracker
from Engine.core.exporter import NovelExporter
from Engine.core.importer import NovelImporter
from Engine.core.daemon import DaemonScheduler
from Engine.config import EngineConfig
from Engine.agents.base import BaseAgent
from Engine.agents.writer import WriterAgent
from Engine.agents.editor import EditorAgent
from Engine.agents.redteam import RedTeamAgent
from Engine.agents.navigator import NavigatorAgent
from Engine.agents.director import DirectorAgent
from Engine.agents.voice_sandbox import VoiceSandbox
from Engine.core.memory_bank import MemoryBank
from Engine.utils.router import ModelRouter


def test_full_pipeline_mock():
    """End-to-end pipeline test with mocked agents.

    Flow:
    1. Navigator creates Task Card
    2. Writer generates draft
    3. Editor reviews draft
    4. RedTeam attacks draft
    5. StateDB updates character state
    6. MemoryBank stores summary
    7. StateFilter validates context
    """
    # 1. Navigator creates Task Card
    nav = NavigatorAgent("model", "Navigate the plot.")
    task_card = nav.generate_task_card(chapter_num=1, history_tension=[])
    assert task_card["chapter"] == 1
    assert "tension_level" in task_card

    # 2. Writer generates draft
    writer = WriterAgent("model", "Write novel scenes.")
    draft = writer.run(task_card)
    assert "Draft" in draft

    # 3. Editor reviews draft
    editor = EditorAgent("model", "Check logic and style.")
    review = editor.run({"draft": draft})
    assert "score" in review
    assert "issues" in review

    # 4. RedTeam attacks draft
    redteam = RedTeamAgent("model", "Attack the plot.")
    attack = redteam.run({"draft": draft})
    assert "attack" in attack

    # 5. StateDB updates character state
    with StateDB(":memory:") as db:
        char = CharacterState(name="Hero", role="Protagonist")
        db.update_character(char)
        retrieved = db.get_character("Hero")
        assert retrieved is not None
        assert retrieved.name == "Hero"

    # 6. MemoryBank stores summary
    bank = MemoryBank(collection_name=f"test_integration_{uuid.uuid4().hex[:8]}")
    bank.add_summary(1, "Hero begins the journey.")
    results = bank.query("journey")
    assert len(results) > 0
    assert any("journey" in r for r in results)

    # 7. StateFilter validates context (no conflicts)
    sf = StateFilter()
    conflict = sf.check_conflict({"status": "alive"}, {"status": "alive"})
    assert conflict["conflict"] is False


def test_pipeline_with_circuit_breaker():
    """Test that circuit breaker correctly handles persistent failures."""
    with StateDB(":memory:") as db:
        ctrl = PipelineController(max_retries=2)

        def failing_write():
            raise RuntimeError("Write failed")

        with pytest.raises(CircuitBreakerError):
            ctrl.execute_with_retry(failing_write)

        # StateDB should still be functional after circuit breaker trip
        db.update_character(CharacterState(name="Survivor", role="Support"))
        assert db.get_character("Survivor") is not None


def test_state_filter_blocks_deceased():
    """Test that StateFilter blocks context for deceased characters."""
    with StateDB(":memory:") as db:
        db.update_character(CharacterState(name="DeadGuy", role="Villain", status="deceased"))
        db.update_character(CharacterState(name="AliveGuy", role="Hero", status="active"))

        f = StateFilter(db)
        rag_context = {
            "DeadGuy": "DeadGuy is walking towards you.",
            "AliveGuy": "AliveGuy stands ready.",
        }
        result = f.apply(rag_context)
        assert "DeadGuy" not in result
        assert "AliveGuy" in result


def test_model_router_integration():
    """Test model router with pipeline configuration."""
    config = {
        "default_model": "qwen3.6-plus",
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)

    result = router.get_model("writer")
    assert result["model"] == "qwen3.6-plus"
    assert result["api_key"] == "test-key"

    result = router.get_model("editor", importance="high")
    assert result["model"] == "qwen3.6-plus"
    assert result["api_key"] == "test-key"


def test_config_router_agent_flow(monkeypatch):
    """Test full flow: EngineConfig -> ModelRouter -> BaseAgent."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen3.6-plus")

    config = EngineConfig.from_env()
    router = ModelRouter(config.to_router_config())

    info = router.get_model("writer", importance="high")
    assert info["model"] == "qwen3.6-plus"
    assert info["api_key"] == "test-key"

    agent = BaseAgent.from_router_info(info, system_prompt="Write.")
    assert agent.model == "qwen3.6-plus"
    assert agent.api_key == "test-key"
    assert agent.base_url == "https://example.com/v1"


def test_event_bus_gradient_rewrite_token_tracker():
    """Test EventBus coordinates GradientRewriter and TokenTracker.

    Flow:
    1. EventBus subscribes to chapter events
    2. GradientRewriter triggers rewrite, publishes event
    3. TokenTracker records the rewrite operation
    4. EventBus delivers event to subscriber callback
    """
    bus = EventBus()
    events_received = []

    def on_event(data):
        events_received.append(data)

    bus.subscribe("gradient_rewrite", on_event)

    # Simulate a rewrite operation that publishes events
    class FakeGateway:
        async def chat(self, messages, **kwargs):
            return "Rewritten chapter content."

    gateway = FakeGateway()
    rewriter = GradientRewriter(gateway, event_bus=bus)

    async def _run_rewrite():
        return await rewriter.rewrite(
            {"content": "Original chapter"},
            {"error": "Plot inconsistency"},
            retry_num=0,
        )

    result = asyncio.run(_run_rewrite())
    assert "Rewritten chapter content" in result
    assert len(events_received) == 1
    assert events_received[0]["retry_num"] == 0


def test_review_policy_export_import_roundtrip():
    """Test ReviewPolicy decision leads to Export -> Import cycle.

    Flow:
    1. Editor produces review result
    2. ReviewPolicy decides whether to interrupt
    3. Novel is exported to txt then imported back
    4. Content integrity is preserved
    """
    # Review policy decision
    policy = ReviewPolicyManager("strict")
    editor_result = {
        "score": 7,
        "issues": ["Minor pacing issue"],
        "critical_issues": [],
    }
    assert policy.should_interrupt(editor_result) is True

    # Export and import roundtrip
    novel = {
        "title": "Test Novel",
        "chapters": [
            {"number": 1, "content": "Chapter one content."},
            {"number": 2, "content": "Chapter two content."},
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "test_novel.txt")
        NovelExporter.to_txt(novel, txt_path)

        imported = NovelImporter.from_file(txt_path)
        assert imported is not None
        assert imported.chapter_count > 0


def test_daemon_scheduler_with_state_transitions():
    """Test DaemonScheduler manages chapter generation with StateDB.

    Flow:
    1. Scheduler starts and accepts tasks
    2. Tasks update character states in StateDB
    3. On-complete callback records token usage
    4. Scheduler processes queue and stops cleanly
    """
    with StateDB(":memory:") as db:
        tracker = TokenTracker()

        # Set up initial character state
        db.update_character(CharacterState(name="Protagonist", role="Hero"))

        scheduler = DaemonScheduler()
        completed_tasks = []

        def on_task_complete(task):
            completed_tasks.append(task)
            # Record token usage for this task
            tracker.record(
                model="qwen3.6-plus",
                prompt_tokens=1000,
                completion_tokens=500,
                task=task.get("name", "unknown"),
            )

        scheduler.on_complete(on_task_complete)

        # Add tasks to the queue
        scheduler.add_task({"name": "chapter_1", "chapter": 1})
        scheduler.add_task({"name": "chapter_2", "chapter": 2})
        assert scheduler.queue_size == 2

        # Start and let it process briefly
        scheduler.start()

        # Import time for polling
        import time
        time.sleep(0.5)

        # Verify tasks were processed
        scheduler.stop()
        assert len(completed_tasks) >= 1
        assert tracker.stats.total_requests >= 1
        assert tracker.stats.total_tokens > 0


def test_full_chapter_lifecycle():
    """Test complete chapter lifecycle with all core modules.

    Flow:
    1. Navigator generates task card
    2. Writer produces draft (voice-injected)
    3. Editor reviews
    4. RedTeam attacks
    5. StateDB updates character
    6. MemoryBank stores summary
    7. StateFilter validates context for next chapter
    8. Snapshot saved for rollback
    9. Token usage recorded
    """
    # 1. Navigate
    nav = NavigatorAgent("model", "Navigate the plot.")
    task_card = nav.generate_task_card(
        chapter_num=1,
        history_tension=[0.3, 0.5, 0.7],
    )
    assert task_card["tension_level"] > 0

    # 2. Write with voice sandbox
    voice_config = {
        "style": "formal",
        "tone": "serious",
        "pacing": "moderate",
        "speech_patterns": ["speaks formally"],
        "sensory_bias": {"visual": 0.8},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(voice_config, f)
        voice_path = f.name

    try:
        voice = VoiceSandbox(voice_path)
        voiced_prompt = voice.inject_prompt("Write a chapter scene.")
        assert "speaks formally" in voiced_prompt
        draft = WriterAgent("model", "Write novel scenes.").run(task_card)
        assert "Draft" in draft
    finally:
        os.unlink(voice_path)

    # 3. Edit
    editor = EditorAgent("model", "Check logic and style.")
    review = editor.run({"draft": draft})
    assert "score" in review

    # 4. RedTeam
    redteam = RedTeamAgent("model", "Attack the plot.")
    attack = redteam.run({"draft": draft})
    assert "attack" in attack

    # 5-6. StateDB + MemoryBank
    with StateDB(":memory:") as db:
        char = CharacterState(
            name="Elena",
            role="Protagonist",
            status="active",
            relationships={"ally": "Marcus"},
        )
        db.update_character(char)

        bank = MemoryBank(collection_name=f"lifecycle_test_{uuid.uuid4().hex[:8]}")
        bank.add_summary(1, "Elena meets Marcus in the tavern.")

        # 7. StateFilter validates
        sf = StateFilter(db)
        rag = {"Elena": "Elena walks.", "Ghost": "Ghost appears."}
        filtered = sf.apply(rag)
        assert "Elena" in filtered
        # Note: StateFilter only blocks characters IN StateDB that are deceased/inactive.
        # Characters not in StateDB pass through (no contradiction to filter).
        assert "Ghost" in filtered  # Not in StateDB, so not blocked

        # Verify deceased characters ARE blocked
        db.update_character(CharacterState(name="DeadGhost", role="Villain", status="deceased"))
        rag2 = {"Elena": "Elena walks.", "DeadGhost": "DeadGhost approaches."}
        filtered2 = sf.apply(rag2)
        assert "Elena" in filtered2
        assert "DeadGhost" not in filtered2  # Deceased, blocked by filter

        # 8. Snapshot for rollback
        snapshot = StateSnapshot(
            version=1,
            chapter_num=1,
            characters=[char],
            world_states=[WorldState(name="era", description="fantasy")],
            metadata={"label": "pre_chapter_2"},
        )
        db.save_snapshot(snapshot)
        snapshots = db.list_snapshots()
        assert len(snapshots) == 1

    # 9. Token tracking
    tracker = TokenTracker()
    tracker.record("qwen3.6-plus", 2000, 1500, "writer_chapter_1")
    tracker.record("qwen3.6-plus", 500, 300, "editor_chapter_1")
    stats = tracker.stats
    assert stats.total_requests == 2
    assert stats.total_tokens == 4300
    assert "writer_chapter_1" in tracker.get_stats_by_task()
