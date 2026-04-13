"""State-Over-Vector Filter: ensures RAG context never contradicts StateDB truth."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from Engine.core.state_db import StateDB


class StateFilter:
    """Hard truth filter: StateDB wins over RAG recall.

    Two modes:
    1. apply(rag_context) -> filtered dict (blocks deceased/inactive characters)
    2. check_conflict(state_db_data, rag_data) -> conflict report dict
    """

    def __init__(self, state_db: Optional[StateDB] = None):
        self.db = state_db

    def apply(self, rag_context: Dict[str, str]) -> Dict[str, str]:
        """Filter RAG context, blocking entries that contradict StateDB truth.

        If a character is deceased/inactive in StateDB, their RAG context is removed.
        """
        safe_context: Dict[str, str] = {}
        for name, text in rag_context.items():
            if self.db:
                char = self.db.get_character(name)
                if char and not char.is_alive:
                    continue
            safe_context[name] = text
        return safe_context

    def check_conflict(
        self,
        state_db_data: Dict[str, Any],
        rag_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if RAG data conflicts with StateDB data.

        Returns dict with:
        - conflict: bool
        - blocked: bool
        - conflicting_keys: list of keys that differ
        """
        conflicting_keys: List[str] = []
        shared_keys = set(state_db_data.keys()) & set(rag_data.keys())

        for key in shared_keys:
            if state_db_data[key] != rag_data[key]:
                conflicting_keys.append(key)

        has_conflict = len(conflicting_keys) > 0
        return {
            "conflict": has_conflict,
            "blocked": has_conflict,
            "conflicting_keys": conflicting_keys,
        }
