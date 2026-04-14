"""Multi-project management with project-scoped StateDB."""
from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProjectInfo:
    id: str
    title: str
    genre: str = "unknown"
    created_at: str = ""
    last_modified: str = ""
    db_path: str = ""
    status: str = "active"  # "active", "archived", "deleted"


class ProjectManager:
    """Manages multiple novel projects, each with its own StateDB."""

    def __init__(self, projects_dir: str = ".projects"):
        self._projects_dir = projects_dir
        os.makedirs(projects_dir, exist_ok=True)
        self._catalog_path = os.path.join(projects_dir, "catalog.db")
        self._init_catalog()

    def _init_catalog(self) -> None:
        """Initialize the project catalog database."""
        with sqlite3.connect(self._catalog_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    genre TEXT DEFAULT 'unknown',
                    created_at TEXT,
                    last_modified TEXT,
                    db_path TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.commit()

    def create_project(self, title: str, genre: str = "unknown") -> ProjectInfo:
        """Create a new project with its own StateDB."""
        project_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        db_path = os.path.join(self._projects_dir, f"{project_id}.db")

        info = ProjectInfo(
            id=project_id,
            title=title,
            genre=genre,
            created_at=now,
            last_modified=now,
            db_path=db_path,
        )

        with sqlite3.connect(self._catalog_path) as conn:
            conn.execute(
                "INSERT INTO projects (id, title, genre, created_at, last_modified, db_path) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, title, genre, now, now, db_path),
            )
            conn.commit()

        # Initialize StateDB tables for the project
        from Engine.core.state_db import StateDB
        db = StateDB(db_path)
        # Initialize the database (creates tables)
        db.get_character("placeholder")
        db.delete_character("placeholder")
        db.close()

        return info

    def list_projects(self, status: str = "active") -> list[ProjectInfo]:
        """List all projects with the given status."""
        with sqlite3.connect(self._catalog_path) as conn:
            cursor = conn.execute(
                "SELECT id, title, genre, created_at, last_modified, db_path, status "
                "FROM projects WHERE status = ?",
                (status,),
            )
            return [
                ProjectInfo(
                    id=row[0],
                    title=row[1],
                    genre=row[2],
                    created_at=row[3],
                    last_modified=row[4],
                    db_path=row[5],
                    status=row[6],
                )
                for row in cursor.fetchall()
            ]

    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID."""
        with sqlite3.connect(self._catalog_path) as conn:
            cursor = conn.execute(
                "SELECT id, title, genre, created_at, last_modified, db_path, status "
                "FROM projects WHERE id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            if row:
                return ProjectInfo(
                    id=row[0],
                    title=row[1],
                    genre=row[2],
                    created_at=row[3],
                    last_modified=row[4],
                    db_path=row[5],
                    status=row[6],
                )
        return None

    def delete_project(self, project_id: str) -> bool:
        """Soft-delete a project."""
        with sqlite3.connect(self._catalog_path) as conn:
            cursor = conn.execute(
                "SELECT db_path FROM projects WHERE id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False

            conn.execute(
                "UPDATE projects SET status = 'deleted' WHERE id = ?",
                (project_id,),
            )
            conn.commit()
            return True

    def archive_project(self, project_id: str) -> bool:
        """Archive a project."""
        with sqlite3.connect(self._catalog_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM projects WHERE id = ?",
                (project_id,),
            )
            if not cursor.fetchone():
                return False
            conn.execute(
                "UPDATE projects SET status = 'archived' WHERE id = ?",
                (project_id,),
            )
            conn.commit()
            return True
