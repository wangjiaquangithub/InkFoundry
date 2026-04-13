"""MemoryBank - Vector memory for chapter summaries (ChromaDB placeholder)."""
from __future__ import annotations

from typing import Any, Dict, List


class MemoryBank:
    """Stores and retrieves chapter summaries for long-context recall.

    Currently uses in-memory list as placeholder for ChromaDB integration.
    """

    def __init__(self):
        self.index: List[Dict[str, Any]] = []

    def add_summary(self, chapter_num: int, text: str) -> None:
        """Store a chapter summary."""
        self.index.append({"ch": chapter_num, "text": text})

    def query(self, keyword: str) -> List[Dict[str, Any]]:
        """Retrieve summaries matching the keyword.

        Args:
            keyword: Search term to match against summary text.

        Returns:
            List of matching summary dicts.
        """
        return [item for item in self.index if keyword.lower() in item["text"].lower()]
