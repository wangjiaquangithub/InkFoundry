"""Tests for MemoryBank (vector store placeholder)."""
from Engine.core.memory_bank import MemoryBank


def test_add_and_query_summary():
    bank = MemoryBank()
    bank.add_summary(1, "Protagonist finds sword.")
    results = bank.query("sword")
    assert len(results) > 0


def test_query_returns_correct_chapter():
    bank = MemoryBank()
    bank.add_summary(1, "Alice meets Bob.")
    bank.add_summary(2, "Charlie finds sword.")
    results = bank.query("sword")
    assert len(results) == 1
    assert results[0]["ch"] == 2


def test_query_no_match():
    bank = MemoryBank()
    bank.add_summary(1, "Alice goes home.")
    results = bank.query("dragon")
    assert len(results) == 0


def test_add_multiple_summaries():
    bank = MemoryBank()
    for i in range(5):
        bank.add_summary(i, f"Chapter {i} summary.")
    assert len(bank.index) == 5
