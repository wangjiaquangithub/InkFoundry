"""SQLite StateDB with atomic locking and version-based concurrency."""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from Engine.core.models import CharacterState, WorldState, StateSnapshot


class StateDB:
    """SQLite-backed state store with atomic locking and snapshots."""

    def __init__(self, db_path: str = "state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            # Generic key-value state table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    lock_id TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            # Character states table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            # World states table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS world_states (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            # Snapshots table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    version INTEGER PRIMARY KEY,
                    chapter_num INTEGER NOT NULL,
                    data TEXT NOT NULL
                )
            """)

    # --- Generic Key-Value State Operations ---

    def get_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve state by key."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT data FROM state WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def update_state(
        self,
        key: str,
        data: Dict[str, Any],
        lock_id: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> None:
        """Update state with optional atomic lock and version check."""
        self._ensure_open()
        with self.lock:
            # Check lock
            if lock_id:
                cursor = self.conn.execute(
                    "SELECT lock_id FROM state WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row and row[0] and row[0] != lock_id:
                    raise RuntimeError(f"State '{key}' is locked by '{row[0]}'")

            # Version check (optimistic concurrency)
            if expected_version is not None:
                cursor = self.conn.execute(
                    "SELECT version FROM state WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row and row[0] != expected_version:
                    raise ValueError(
                        f"Version mismatch: expected {expected_version}, "
                        f"got {row[0]}"
                    )

            new_version = data.get("version", 1)
            with self.conn:
                self.conn.execute(
                    """INSERT OR REPLACE INTO state (key, data, lock_id, version)
                       VALUES (?, ?, ?, ?)""",
                    (key, json.dumps(data), lock_id, new_version),
                )

    def release_lock(self, key: str, lock_id: str) -> None:
        """Release an atomic lock on a state key."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "UPDATE state SET lock_id = NULL WHERE key = ? AND lock_id = ?",
                    (key, lock_id),
                )

    # --- Character CRUD ---

    def update_character(self, char: CharacterState) -> None:
        """Store or update a character state."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO characters (name, data) VALUES (?, ?)",
                    (char.name, char.model_dump_json()),
                )

    def get_character(self, name: str) -> Optional[CharacterState]:
        """Retrieve a character state by name."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT data FROM characters WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        if row:
            return CharacterState.model_validate_json(row[0])
        return None

    def delete_character(self, name: str) -> bool:
        """Delete a character state by name.

        Returns:
            True if the character was deleted, False if not found.
        """
        self._ensure_open()
        with self.lock:
            with self.conn:
                cursor = self.conn.execute(
                    "DELETE FROM characters WHERE name = ?", (name,)
                )
                return cursor.rowcount > 0

    # --- World State CRUD ---

    def update_world_state(self, world: WorldState) -> None:
        """Store or update a world state."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO world_states (name, data) VALUES (?, ?)",
                    (world.name, world.model_dump_json()),
                )

    def get_world_state(self, name: str) -> Optional[WorldState]:
        """Retrieve a world state by name."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT data FROM world_states WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        if row:
            return WorldState.model_validate_json(row[0])
        return None

    # --- Snapshot Management ---

    def save_snapshot(self, snapshot: StateSnapshot) -> None:
        """Save a state snapshot."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO snapshots (version, chapter_num, data) VALUES (?, ?, ?)",
                    (snapshot.version, snapshot.chapter_num, snapshot.model_dump_json()),
                )

    def load_snapshot(self, version: int) -> Optional[StateSnapshot]:
        """Load a state snapshot by version."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT data FROM snapshots WHERE version = ?", (version,)
        )
        row = cursor.fetchone()
        if row:
            return StateSnapshot.model_validate_json(row[0])
        return None

    def list_snapshots(self) -> List[StateSnapshot]:
        """List all snapshots ordered by version."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT data FROM snapshots ORDER BY version ASC"
        )
        return [StateSnapshot.model_validate_json(row[0]) for row in cursor.fetchall()]

    # --- Lifecycle ---

    def __enter__(self) -> "StateDB":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _ensure_open(self) -> None:
        if self.conn is None:
            raise RuntimeError("Database connection is closed")
