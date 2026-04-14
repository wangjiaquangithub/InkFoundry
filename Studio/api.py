"""Studio FastAPI backend - REST API for the UI dashboard."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState


class CharacterCreate(BaseModel):
    name: str
    role: str
    status: str = "active"


def create_app() -> FastAPI:
    """Create and configure the Studio FastAPI application."""
    app = FastAPI(title="InkFoundry Studio")

    # In-memory StateDB for Studio API (separate from Engine's persistent db)
    db = StateDB(":memory:")

    @app.get("/status")
    def get_status() -> Dict[str, str]:
        """Get the current system status."""
        return {"status": "running"}

    @app.get("/health")
    def health_check() -> Dict[str, bool]:
        """Health check endpoint."""
        return {"healthy": True}

    @app.get("/characters")
    def list_characters() -> Dict[str, List[Dict[str, Any]]]:
        """List all characters."""
        cursor = db.conn.execute("SELECT data FROM characters")
        chars = []
        for row in cursor.fetchall():
            chars.append(CharacterState.model_validate_json(row[0]).model_dump())
        return {"characters": chars}

    @app.post("/characters")
    def create_character(char: CharacterCreate) -> Dict[str, str]:
        """Create a new character."""
        state = CharacterState(name=char.name, role=char.role, status=char.status)
        db.update_character(state)
        return {"message": f"Character '{char.name}' created"}

    @app.get("/characters/{name}")
    def get_character(name: str) -> Dict[str, Any]:
        """Get a specific character."""
        char = db.get_character(name)
        if char is None:
            return {"error": f"Character '{name}' not found"}
        return char.model_dump()

    # --- Static file serving for React SPA ---
    FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

    if os.path.exists(FRONTEND_DIST):
        app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> Any:
        """Serve React SPA - fallback to index.html for all non-API routes."""
        if full_path.startswith(("api/", "health", "docs", "openapi.json", "status", "characters")):
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
