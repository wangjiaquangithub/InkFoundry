"""SQLite StateDB with atomic locking and version-based concurrency."""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from Engine.core.models import (
    CharacterState, CharacterProfile, CharacterRelationship,
    WorldState, WorldBuilding, PowerSystem, Timeline,
    StateSnapshot, Outline, Chapter,
)


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
            # Chapters table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chapters (
                    chapter_num INTEGER PRIMARY KEY,
                    title TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    word_count INTEGER DEFAULT 0,
                    tension_level INTEGER DEFAULT 5,
                    version INTEGER DEFAULT 1,
                    review_notes TEXT DEFAULT '',
                    agent_results TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            # Outline table (single outline per project)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS outlines (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    title TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    total_chapters INTEGER DEFAULT 100,
                    arc TEXT DEFAULT 'hero_journey',
                    volume_plans TEXT DEFAULT '[]',
                    chapter_summaries TEXT DEFAULT '[]',
                    tension_curve TEXT DEFAULT '[]',
                    foreshadowing TEXT DEFAULT '[]',
                    genre_rules TEXT DEFAULT '[]'
                )
            """)
            # Character profiles table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS character_profiles (
                    name TEXT PRIMARY KEY,
                    gender TEXT DEFAULT '',
                    age INTEGER DEFAULT 0,
                    appearance TEXT DEFAULT '',
                    personality TEXT DEFAULT '',
                    backstory TEXT DEFAULT '',
                    motivation TEXT DEFAULT '',
                    voice_profile_ref TEXT DEFAULT 'default'
                )
            """)
            # Character relationships table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS character_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_character TEXT NOT NULL,
                    to_character TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    strength REAL DEFAULT 0.5
                )
            """)
            # World building table (single entry)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS world_building (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    name TEXT NOT NULL,
                    era TEXT DEFAULT '',
                    geography TEXT DEFAULT '',
                    social_structure TEXT DEFAULT '',
                    technology_level TEXT DEFAULT '',
                    cultures TEXT DEFAULT '[]',
                    factions TEXT DEFAULT '[]'
                )
            """)
            # Power systems table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS power_systems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    levels TEXT NOT NULL DEFAULT '[]',
                    rules TEXT DEFAULT ''
                )
            """)
            # Timeline table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS timelines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    impact TEXT DEFAULT ''
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

    # --- Chapter CRUD ---

    def update_chapter(self, chapter: Chapter) -> None:
        """Store or update a chapter. Auto-increments version on update."""
        self._ensure_open()
        with self.lock:
            # Get existing version to increment
            cursor = self.conn.execute(
                "SELECT version, created_at FROM chapters WHERE chapter_num = ?",
                (chapter.chapter_num,),
            )
            existing = cursor.fetchone()
            new_version = existing[0] + 1 if existing else chapter.version
            created_at = existing[1] if existing else None

            with self.conn:
                self.conn.execute(
                    """INSERT OR REPLACE INTO chapters
                       (chapter_num, title, content, status, word_count,
                        tension_level, version, review_notes, agent_results,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                               COALESCE(?, datetime('now')), datetime('now'))""",
                    (chapter.chapter_num, chapter.title, chapter.content,
                     chapter.status, chapter.word_count, chapter.tension_level,
                     new_version, chapter.review_notes,
                     chapter.model_dump_json(exclude={
                         'chapter_num', 'title', 'content', 'status',
                         'word_count', 'tension_level', 'version',
                         'review_notes', 'created_at', 'updated_at',
                     }),
                     created_at),
                )

    def get_chapter(self, chapter_num: int) -> Optional[Chapter]:
        """Retrieve a chapter by number."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT * FROM chapters WHERE chapter_num = ?", (chapter_num,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["agent_results"] = json.loads(d.get("agent_results", "{}"))
        return Chapter(**d)

    def list_chapters(self) -> List[Chapter]:
        """List all chapters ordered by chapter_num."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT * FROM chapters ORDER BY chapter_num ASC"
        )
        chapters = []
        for row in cursor.fetchall():
            d = dict(row)
            d["agent_results"] = json.loads(d.get("agent_results", "{}"))
            chapters.append(Chapter(**d))
        return chapters

    def delete_chapter(self, chapter_num: int) -> bool:
        """Delete a chapter."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                cursor = self.conn.execute(
                    "DELETE FROM chapters WHERE chapter_num = ?", (chapter_num,)
                )
                return cursor.rowcount > 0

    # --- Outline CRUD ---

    def save_outline(self, outline: Outline) -> None:
        """Save or update the project outline."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    """INSERT OR REPLACE INTO outlines
                       (id, title, summary, total_chapters, arc,
                        volume_plans, chapter_summaries, tension_curve,
                        foreshadowing, genre_rules)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (outline.title, outline.summary, outline.total_chapters,
                     outline.arc, json.dumps(outline.volume_plans),
                     json.dumps(outline.chapter_summaries),
                     json.dumps(outline.tension_curve),
                     json.dumps(outline.foreshadowing),
                     json.dumps(outline.genre_rules)),
                )

    def get_outline(self) -> Optional[Outline]:
        """Retrieve the project outline."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM outlines WHERE id = 1")
        row = cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        for key in ("volume_plans", "chapter_summaries", "tension_curve",
                     "foreshadowing", "genre_rules"):
            d[key] = json.loads(d[key])
        d.pop("id", None)
        return Outline(**d)

    # --- Character Profiles ---

    def save_character_profile(self, profile: CharacterProfile) -> None:
        """Save a character profile."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    """INSERT OR REPLACE INTO character_profiles
                       (name, gender, age, appearance, personality,
                        backstory, motivation, voice_profile_ref)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (profile.name, profile.gender, profile.age,
                     profile.appearance, profile.personality,
                     profile.backstory, profile.motivation,
                     profile.voice_profile_ref),
                )

    def get_character_profile(self, name: str) -> Optional[CharacterProfile]:
        """Retrieve a character profile."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT * FROM character_profiles WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return CharacterProfile(**dict(row))

    def list_character_profiles(self) -> List[CharacterProfile]:
        """List all character profiles."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM character_profiles")
        return [CharacterProfile(**dict(row)) for row in cursor.fetchall()]

    # --- Character Relationships ---

    def add_character_relationship(self, rel: CharacterRelationship) -> None:
        """Add a character relationship."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO character_relationships
                       (from_character, to_character, relationship_type,
                        description, strength)
                       VALUES (?, ?, ?, ?, ?)""",
                    (rel.from_character, rel.to_character, rel.relationship_type,
                     rel.description, rel.strength),
                )

    def get_character_relationships(self, character_name: str) -> List[CharacterRelationship]:
        """Get relationships for a character."""
        self._ensure_open()
        cursor = self.conn.execute(
            "SELECT * FROM character_relationships WHERE from_character = ? OR to_character = ?",
            (character_name, character_name),
        )
        return [CharacterRelationship(**dict(row)) for row in cursor.fetchall()]

    def list_all_relationships(self) -> List[CharacterRelationship]:
        """List all character relationships."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM character_relationships")
        return [CharacterRelationship(**dict(row)) for row in cursor.fetchall()]

    # --- World Building ---

    def save_world_building(self, wb: WorldBuilding) -> None:
        """Save world building settings."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    """INSERT OR REPLACE INTO world_building
                       (id, name, era, geography, social_structure,
                        technology_level, cultures, factions)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                    (wb.name, wb.era, wb.geography, wb.social_structure,
                     wb.technology_level, json.dumps(wb.cultures),
                     json.dumps(wb.factions)),
                )

    def get_world_building(self) -> Optional[WorldBuilding]:
        """Retrieve world building settings."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM world_building WHERE id = 1")
        row = cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d.pop("id", None)
        d["cultures"] = json.loads(d["cultures"])
        d["factions"] = json.loads(d["factions"])
        return WorldBuilding(**d)

    # --- Power Systems ---

    def add_power_system(self, ps: PowerSystem) -> None:
        """Add a power system."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO power_systems (name, levels, rules) VALUES (?, ?, ?)",
                    (ps.name, json.dumps(ps.levels), ps.rules),
                )

    def get_power_systems(self) -> List[PowerSystem]:
        """List all power systems."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM power_systems")
        systems = []
        for row in cursor.fetchall():
            d = dict(row)
            d["levels"] = json.loads(d["levels"])
            d.pop("id", None)
            systems.append(PowerSystem(**d))
        return systems

    # --- Timeline ---

    def add_timeline_event(self, tl: Timeline) -> None:
        """Add a timeline event."""
        self._ensure_open()
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO timelines (year, event, impact) VALUES (?, ?, ?)",
                    (tl.year, tl.event, tl.impact),
                )

    def get_timeline(self) -> List[Timeline]:
        """List timeline events ordered by year."""
        self._ensure_open()
        cursor = self.conn.execute("SELECT * FROM timelines ORDER BY year ASC")
        return [Timeline(**dict(row)) for row in cursor.fetchall()]

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
