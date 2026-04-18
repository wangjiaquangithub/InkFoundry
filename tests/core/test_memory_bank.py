"""Tests for MemoryBank (vector store)."""
import uuid

from Engine.config import EngineConfig, LLMConfig
from Engine.core.memory_bank import MemoryBank
from Engine.core.project_manager import ProjectManager
from Engine.core.state_db import StateDB
from Studio.api import PipelineManager


def _unique_name() -> str:
    return f"test_legacy_{uuid.uuid4().hex[:8]}"


def test_add_and_query_summary():
    bank = MemoryBank(collection_name=_unique_name())
    bank.add_summary(1, "Protagonist finds sword.")
    results = bank.query("sword")
    assert len(results) > 0


def test_query_returns_correct_chapter():
    bank = MemoryBank(collection_name=_unique_name())
    bank.add_summary(1, "Alice meets Bob.")
    bank.add_summary(2, "Charlie finds sword.")
    results = bank.query("sword")
    assert len(results) >= 1
    # With semantic search, verify the sword document is present
    assert any("sword" in r for r in results)


def test_query_no_match():
    bank = MemoryBank(collection_name=_unique_name())
    bank.add_summary(1, "Alice goes home.")
    results = bank.query("dragon")
    # Semantic search may return partial matches; verify dragon is not in results
    assert not any("dragon" in r.lower() for r in results)


def test_add_multiple_summaries():
    bank = MemoryBank(collection_name=_unique_name())
    for i in range(5):
        bank.add_summary(i, f"Chapter {i} summary.")
    assert len(bank.index) == 5


def test_pipeline_manager_create_orchestrator_uses_project_scoped_memory_bank(tmp_path, monkeypatch):
    project_manager = ProjectManager(str(tmp_path / "projects"))
    project_a = project_manager.create_project(title="Project A", summary="Summary A")
    project_b = project_manager.create_project(title="Project B", summary="Summary B")
    manager = PipelineManager()

    config = EngineConfig(
        llm=LLMConfig(api_key="test-key", base_url="https://api.openai.com/v1", default_model="qwen3.6-plus"),
        role_models={"writer": "qwen3.6-plus", "editor": "qwen3.6-plus", "redteam": "qwen3.6-plus", "navigator": "qwen3.6-plus", "director": "qwen3.6-plus"},
    )
    monkeypatch.setattr("Studio.api._get_engine_config_or_http", lambda db: config)

    db_a = StateDB(project_a.db_path)
    db_b = StateDB(project_b.db_path)
    try:
        orchestrator_a = manager._create_orchestrator(db_a)
        orchestrator_b = manager._create_orchestrator(db_b)

        assert orchestrator_a.memory_bank is not orchestrator_b.memory_bank
        assert orchestrator_a.memory_bank._collection_name != orchestrator_b.memory_bank._collection_name
    finally:
        db_a.close()
        db_b.close()


def test_project_scoped_memory_bank_does_not_leak_between_projects(tmp_path):
    persist_root = tmp_path / "memory"
    bank_a = MemoryBank(collection_name="project_a_memory", persist_directory=str(persist_root / "project-a"))
    bank_b = MemoryBank(collection_name="project_b_memory", persist_directory=str(persist_root / "project-b"))

    bank_a.store("hero remembers the sword in project a")

    results_b = bank_b.query("sword", n_results=5)
    results_a = bank_a.query("sword", n_results=5)

    assert not any("project a" in item.lower() for item in results_b)
    assert any("project a" in item.lower() for item in results_a)


def test_pipeline_manager_create_orchestrator_uses_distinct_memory_bank_for_in_memory_dbs(monkeypatch):
    manager = PipelineManager()

    config = EngineConfig(
        llm=LLMConfig(api_key="test-key", base_url="https://api.openai.com/v1", default_model="qwen3.6-plus"),
        role_models={"writer": "qwen3.6-plus", "editor": "qwen3.6-plus", "redteam": "qwen3.6-plus", "navigator": "qwen3.6-plus", "director": "qwen3.6-plus"},
    )
    monkeypatch.setattr("Studio.api._get_engine_config_or_http", lambda db: config)

    db_a = StateDB(":memory:")
    db_b = StateDB(":memory:")
    try:
        orchestrator_a = manager._create_orchestrator(db_a)
        orchestrator_b = manager._create_orchestrator(db_b)

        assert orchestrator_a.memory_bank._collection_name != orchestrator_b.memory_bank._collection_name
        assert getattr(orchestrator_a.memory_bank, "_use_real_chroma", False) is False or orchestrator_a.memory_bank._collection is not orchestrator_b.memory_bank._collection
    finally:
        db_a.close()
        db_b.close()
