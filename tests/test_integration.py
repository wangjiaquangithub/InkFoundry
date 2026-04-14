"""Integration test - full pipeline end-to-end with mocked LLM calls."""
import pytest
from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState, WorldState, StateSnapshot
from Engine.core.filter import StateFilter
from Engine.core.controller import PipelineController, CircuitBreakerError
from Engine.config import EngineConfig
from Engine.agents.base import BaseAgent
from Engine.agents.writer import WriterAgent
from Engine.agents.editor import EditorAgent
from Engine.agents.redteam import RedTeamAgent
from Engine.agents.navigator import NavigatorAgent
from Engine.agents.director import DirectorAgent
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
    db = StateDB(":memory:")
    char = CharacterState(name="Hero", role="Protagonist")
    db.update_character(char)
    retrieved = db.get_character("Hero")
    assert retrieved is not None
    assert retrieved.name == "Hero"

    # 6. MemoryBank stores summary
    bank = MemoryBank()
    bank.add_summary(1, "Hero begins the journey.")
    results = bank.query("journey")
    assert len(results) > 0

    # 7. StateFilter validates context (no conflicts)
    sf = StateFilter()
    conflict = sf.check_conflict({"status": "alive"}, {"status": "alive"})
    assert conflict["conflict"] is False


def test_pipeline_with_circuit_breaker():
    """Test that circuit breaker correctly handles persistent failures."""
    db = StateDB(":memory:")
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
    db = StateDB(":memory:")
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
        "default_model": "qwen-plus",
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)

    result = router.get_model("writer")
    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "test-key"

    result = router.get_model("editor", importance="high")
    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "test-key"


def test_config_router_agent_flow(monkeypatch):
    """Test full flow: EngineConfig -> ModelRouter -> BaseAgent."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")

    config = EngineConfig.from_env()
    router = ModelRouter(config.to_router_config())

    info = router.get_model("writer", importance="high")
    assert info["model"] == "qwen-plus"
    assert info["api_key"] == "test-key"

    agent = BaseAgent.from_router_info(info, system_prompt="Write.")
    assert agent.model == "qwen-plus"
    assert agent.api_key == "test-key"
    assert agent.base_url == "https://example.com/v1"
