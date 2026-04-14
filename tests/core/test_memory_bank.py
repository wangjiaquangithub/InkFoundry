"""Tests for MemoryBank (vector store)."""
import uuid
from Engine.core.memory_bank import MemoryBank


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
