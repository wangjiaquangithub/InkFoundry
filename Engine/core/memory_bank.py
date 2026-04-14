"""MemoryBank - Vector memory for novel context (ChromaDB backed)."""
from __future__ import annotations

import hashlib
import struct
import uuid
from typing import Any, Dict, List, Optional

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class _SimpleEmbeddingFunction:
    """A lightweight embedding function using text hashing.

    Produces deterministic 384-dimensional vectors from text using
    character n-gram hashing. No external ML dependencies required.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim

    def name(self) -> str:
        return "default"

    def _embed_text(self, text: str) -> List[float]:
        """Embed a single text into a vector."""
        vec = [0.0] * self._dim
        for i in range(max(0, len(text) - 2)):
            trigram = text[i : i + 3]
            h = hashlib.md5(trigram.encode("utf-8")).digest()
            val = struct.unpack("<I", h[:4])[0]
            pos = val % self._dim
            vec[pos] += 1.0
        norm = (sum(v * v for v in vec)) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self._embed_text(text) for text in input]

    def embed_query(self, input: List[str]) -> List[List[float]]:
        """Embed query texts."""
        return self(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        """Embed document texts."""
        return self(input)


class MemoryBank:
    """Stores and retrieves chapter summaries for long-context recall.

    Uses ChromaDB for vector retrieval when available,
    falling back to an in-memory list for tests without chromadb.
    """

    def __init__(
        self,
        collection_name: str = "novel_memory",
        persist_directory: Optional[str] = None,
    ):
        self._collection_name = collection_name

        if HAS_CHROMADB:
            self._embedding_fn = _SimpleEmbeddingFunction()
            if persist_directory:
                self._client = chromadb.PersistentClient(path=persist_directory)
            else:
                self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=self._embedding_fn,
            )
            self._use_real_chroma = True
        else:
            self._documents: List[Dict[str, Any]] = []
            self._use_real_chroma = False

    # --- New vector-store interface ---

    def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a document in the vector memory.

        Args:
            content: The text content to store.
            metadata: Optional metadata dictionary.

        Returns:
            The unique document ID.
        """
        doc_id = str(uuid.uuid4())
        if self._use_real_chroma:
            # ChromaDB v1.x requires non-empty metadata
            meta = metadata.copy() if metadata else {}
            meta["_stored"] = "true"
            self._collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta],
            )
        else:
            self._documents.append({"id": doc_id, "content": content, "metadata": metadata or {}})
        return doc_id

    def query(self, query_text: str, n_results: int = 5) -> List[str]:
        """Retrieve documents matching the query text.

        Args:
            query_text: Search term or semantic query.
            n_results: Maximum number of results to return.

        Returns:
            List of matching document content strings.
        """
        if self._use_real_chroma:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
            return results.get("documents", [[]])[0]
        else:
            return [d["content"] for d in self._documents[-n_results:]]

    def clear(self) -> None:
        """Remove all documents from the memory bank."""
        if self._use_real_chroma:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=self._embedding_fn,
            )
        else:
            self._documents = []

    def count(self) -> int:
        """Return the number of documents in the memory bank."""
        if self._use_real_chroma:
            return self._collection.count()
        return len(self._documents)

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents with their metadata.

        Returns:
            List of dicts with keys: id, content, metadata.
        """
        if self._use_real_chroma:
            results = self._collection.get()
            docs = []
            for i, doc_id in enumerate(results.get("ids", [])):
                # Strip internal metadata prefix
                meta = results.get("metadatas", [{}])[i].copy()
                meta.pop("_stored", None)
                docs.append({
                    "id": doc_id,
                    "content": results.get("documents", [[]])[i],
                    "metadata": meta,
                })
            return docs
        return self._documents

    # --- Legacy interface for backward compatibility ---

    @property
    def index(self) -> List[Dict[str, Any]]:
        """Legacy: return all documents in the old format."""
        if self._use_real_chroma:
            results = self._collection.get()
            docs = []
            for i, doc_id in enumerate(results.get("ids", [])):
                meta = results.get("metadatas", [{}])[i]
                docs.append({
                    "ch": meta.get("chapter", 0),
                    "text": results.get("documents", [[]])[i],
                })
            return docs
        return self._documents

    def add_summary(self, chapter_num: int, text: str) -> None:
        """Store a chapter summary (legacy interface).

        Args:
            chapter_num: The chapter number.
            text: The summary text.
        """
        self.store(text, metadata={"chapter": chapter_num})
