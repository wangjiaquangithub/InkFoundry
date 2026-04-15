"""Studio FastAPI backend - REST API for the UI dashboard."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState


class CharacterCreate(BaseModel):
    name: str
    role: str = "supporting"
    status: str = "active"


class CharacterUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None


class StateSnapshotResponse(BaseModel):
    version: int
    chapter_num: int
    characters: List[Dict[str, Any]]
    world_states: List[Dict[str, Any]]


class ProjectStatus(BaseModel):
    id: str = "novel-001"
    title: str = "Untitled Novel"
    genre: str = "fiction"
    current_chapter: int = 1
    total_chapters: int = 10
    status: str = "idle"


def _get_db(request: Request) -> StateDB:
    """Dependency injection for StateDB."""
    return request.app.state.db


def _seed_sample_data(db: StateDB) -> None:
    """Seed sample characters if DB is empty."""
    cursor = db.conn.execute("SELECT COUNT(*) FROM characters")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_chars = [
            CharacterState(name="林默", role="protagonist", status="active"),
            CharacterState(name="苏晚晴", role="love_interest", status="active"),
            CharacterState(name="陈锋", role="antagonist", status="active"),
        ]
        for char in sample_chars:
            db.update_character(char)


def create_app(seed_data: bool = True) -> FastAPI:
    """Create and configure the Studio FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle with proper resource cleanup."""
        db = StateDB(":memory:")
        app.state.db = db
        if seed_data:
            _seed_sample_data(db)
        yield
        db.close()

    app = FastAPI(title="InkFoundry Studio", lifespan=lifespan)

    # --- Status & Health ---
    @app.get("/status")
    def get_status() -> ProjectStatus:
        """Get the current project status."""
        return ProjectStatus()

    @app.get("/health")
    def health_check() -> Dict[str, bool]:
        """Health check endpoint."""
        return {"healthy": True}

    # --- Characters (no /api prefix) ---
    @app.get("/characters")
    def list_characters(db: StateDB = Depends(_get_db)) -> Dict[str, List[Dict[str, Any]]]:
        """List all characters."""
        cursor = db.conn.execute("SELECT data FROM characters")
        chars = []
        for row in cursor.fetchall():
            chars.append(CharacterState.model_validate_json(row[0]).model_dump())
        return {"characters": chars}

    @app.post("/characters")
    def create_character(char: CharacterCreate, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Create a new character."""
        state = CharacterState(name=char.name, role=char.role, status=char.status)
        db.update_character(state)
        return {"message": f"Character '{char.name}' created"}

    @app.put("/characters/{name}")
    def update_character(name: str, data: CharacterUpdate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Update a character."""
        existing = db.get_character(name)
        if existing is None:
            return {"error": f"Character '{name}' not found"}
        updates = existing.model_dump()
        if data.role is not None:
            updates["role"] = data.role
        if data.status is not None:
            updates["status"] = data.status
        updated = CharacterState(**updates)
        db.update_character(updated)
        return {"message": f"Character '{name}' updated", "character": updated.model_dump()}

    @app.delete("/characters/{name}")
    def delete_character(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Delete a character."""
        existing = db.get_character(name)
        if existing is None:
            return {"error": f"Character '{name}' not found"}
        db.conn.execute("DELETE FROM characters WHERE name = ?", (name,))
        db.conn.commit()
        return {"message": f"Character '{name}' deleted"}

    @app.get("/characters/{name}")
    def get_character(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Get a specific character."""
        char = db.get_character(name)
        if char is None:
            raise HTTPException(status_code=404, detail=f"Character '{name}' not found")
        return char.model_dump()

    # --- State Snapshot ---
    @app.get("/state/snapshot")
    def get_state_snapshot(db: StateDB = Depends(_get_db)) -> StateSnapshotResponse:
        """Get current state snapshot."""
        chars_cursor = db.conn.execute("SELECT data FROM characters")
        ws_cursor = db.conn.execute("SELECT data FROM world_states")
        version_row = db.conn.execute("SELECT MAX(version) FROM snapshots").fetchone()
        return StateSnapshotResponse(
            version=version_row[0] or 0,
            chapter_num=1,
            characters=[CharacterState.model_validate_json(r[0]).model_dump() for r in chars_cursor.fetchall()],
            world_states=[{"name": "default", "description": "", "state": "normal"}],
        )

    # --- WebSocket for pipeline ---
    @app.websocket("/ws/pipeline")
    async def websocket_pipeline(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await asyncio.sleep(5)
                await websocket.send_json({
                    "step": "idle",
                    "agent": None,
                    "progress": 0,
                    "status": "waiting",
                })
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass  # Already closed

    # --- /api/ prefixed routes (for frontend compatibility) ---
    api_router = []

    @app.get("/api/status")
    def api_status() -> ProjectStatus:
        return ProjectStatus()

    @app.get("/api/characters")
    def api_list_characters(db: StateDB = Depends(_get_db)) -> Dict[str, List[Dict[str, Any]]]:
        cursor = db.conn.execute("SELECT data FROM characters")
        chars = []
        for row in cursor.fetchall():
            chars.append(CharacterState.model_validate_json(row[0]).model_dump())
        return {"characters": chars}

    @app.post("/api/characters")
    def api_create_character(char: CharacterCreate, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        state = CharacterState(name=char.name, role=char.role, status=char.status)
        db.update_character(state)
        return {"message": f"Character '{char.name}' created"}

    @app.put("/api/characters/{name}")
    def api_update_character(name: str, data: CharacterUpdate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        existing = db.get_character(name)
        if existing is None:
            return {"error": f"Character '{name}' not found"}
        updates = existing.model_dump()
        if data.role is not None:
            updates["role"] = data.role
        if data.status is not None:
            updates["status"] = data.status
        updated = CharacterState(**updates)
        db.update_character(updated)
        return {"message": f"Character '{name}' updated", "character": updated.model_dump()}

    @app.delete("/api/characters/{name}")
    def api_delete_character(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        existing = db.get_character(name)
        if existing is None:
            return {"error": f"Character '{name}' not found"}
        db.conn.execute("DELETE FROM characters WHERE name = ?", (name,))
        db.conn.commit()
        return {"message": f"Character '{name}' deleted"}

    @app.get("/api/characters/{name}")
    def api_get_character(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        char = db.get_character(name)
        if char is None:
            raise HTTPException(status_code=404, detail=f"Character '{name}' not found")
        return char.model_dump()

    @app.get("/api/state/snapshot")
    def api_state_snapshot(db: StateDB = Depends(_get_db)) -> StateSnapshotResponse:
        chars_cursor = db.conn.execute("SELECT data FROM characters")
        ws_cursor = db.conn.execute("SELECT data FROM world_states")
        version_row = db.conn.execute("SELECT MAX(version) FROM snapshots").fetchone()
        return StateSnapshotResponse(
            version=version_row[0] or 0,
            chapter_num=1,
            characters=[CharacterState.model_validate_json(r[0]).model_dump() for r in chars_cursor.fetchall()],
            world_states=[{"name": "default", "description": "", "state": "normal"}],
        )

    # --- Static file serving for React SPA ---
    FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

    if os.path.exists(FRONTEND_DIST):
        app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> Any:
        """Serve React SPA - fallback to index.html for all non-API routes."""
        if full_path.startswith(("api/", "health", "docs", "openapi.json", "status", "characters", "state/", "ws/")):
            return None  # Let other routes handle API paths
        if not os.path.exists(FRONTEND_DIST):
            return {"status": "API running", "message": "Frontend not built yet. Run: cd frontend && npm run build"}
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"status": "API running", "message": "Frontend not built yet. Run: cd frontend && npm run build"}

    return app


# Default app instance
app = create_app()
