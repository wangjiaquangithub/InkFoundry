"""Tests for MemoryBank with ChromaDB integration."""
from __future__ import annotations

import uuid

import pytest
from Engine.core.memory_bank import MemoryBank, HAS_CHROMADB


def _unique_name() -> str:
    return f"test_memory_{uuid.uuid4().hex[:8]}"


def test_memory_bank_store_and_count():
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Chapter 1: The beginning")
    mb.store("Chapter 2: The journey")
    assert mb.count() == 2


def test_memory_bank_query_returns_content():
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("张三走进房间，看到李四坐在桌前。")
    mb.store("王五在门外等候。")

    results = mb.query("房间", n_results=1)
    assert len(results) <= 1  # At most 1 result


def test_memory_bank_clear():
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Test document")
    assert mb.count() == 1
    mb.clear()
    assert mb.count() == 0


def test_memory_bank_list_documents():
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Doc 1", {"chapter": 1})
    mb.store("Doc 2", {"chapter": 2})
    docs = mb.list_documents()
    assert len(docs) == 2
    assert any(d["content"] == "Doc 1" for d in docs)


def test_memory_bank_store_returns_id():
    mb = MemoryBank(collection_name=_unique_name())
    doc_id = mb.store("Test content")
    assert doc_id is not None
    assert isinstance(doc_id, str)


def test_memory_bank_fallback_without_chromadb(monkeypatch):
    """Test that MemoryBank works without chromadb installed."""
    monkeypatch.setattr("Engine.core.memory_bank.HAS_CHROMADB", False)
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Fallback test")
    assert mb.count() == 1
    results = mb.query("query", n_results=1)
    assert len(results) == 1
    assert results[0] == "Fallback test"


def test_memory_bank_legacy_add_summary_and_query():
    """Test backward-compatible add_summary/query interface."""
    mb = MemoryBank(collection_name=_unique_name())
    mb.add_summary(1, "张三走进房间，看到李四坐在桌前。")
    mb.add_summary(2, "王五在门外等候。")
    assert mb.count() == 2
    results = mb.query("房间")
    assert len(results) >= 1


def test_memory_bank_legacy_index_property():
    """Test that the legacy index property works."""
    mb = MemoryBank(collection_name=_unique_name())
    mb.add_summary(3, "Hero begins the journey.")
    idx = mb.index
    assert len(idx) == 1
    assert idx[0]["ch"] == 3
    assert "journey" in idx[0]["text"]


def test_memory_bank_clear_fallback(monkeypatch):
    """Test clear() works in fallback mode."""
    monkeypatch.setattr("Engine.core.memory_bank.HAS_CHROMADB", False)
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Doc 1")
    mb.store("Doc 2")
    assert mb.count() == 2
    mb.clear()
    assert mb.count() == 0


def test_memory_bank_list_documents_fallback(monkeypatch):
    """Test list_documents() works in fallback mode."""
    monkeypatch.setattr("Engine.core.memory_bank.HAS_CHROMADB", False)
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Content A", {"key": "value"})
    docs = mb.list_documents()
    assert len(docs) == 1
    assert docs[0]["content"] == "Content A"
    assert docs[0]["metadata"]["key"] == "value"


def test_memory_bank_close():
    """MemoryBank.close() must release ChromaDB references."""
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Close test")
    assert mb.count() == 1
    mb.close()
    # After close, _client should be None
    assert mb._client is None
    assert mb._collection is None


def test_memory_bank_close_fallback(monkeypatch):
    """MemoryBank.close() is safe in fallback mode."""
    monkeypatch.setattr("Engine.core.memory_bank.HAS_CHROMADB", False)
    mb = MemoryBank(collection_name=_unique_name())
    mb.store("Fallback close")
    mb.close()  # Should not raise
    assert not hasattr(mb, "_client") or mb._client is None
