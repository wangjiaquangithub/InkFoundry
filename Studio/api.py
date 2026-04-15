"""Studio FastAPI backend - REST API for the UI dashboard."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from Engine.core.state_db import StateDB
from Engine.core.models import (
    CharacterState, Chapter, Outline, CharacterProfile,
    CharacterRelationship, WorldBuilding, PowerSystem, Timeline,
)


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


class ChapterCreate(BaseModel):
    title: str = ""
    content: str = ""


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


class ProfileCreate(BaseModel):
    name: str
    gender: str = ""
    age: int = 0
    appearance: str = ""
    personality: str = ""
    backstory: str = ""
    motivation: str = ""
    voice_profile_ref: str = "default"


class ProfileUpdate(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None
    motivation: Optional[str] = None
    voice_profile_ref: Optional[str] = None


class RelationshipCreate(BaseModel):
    from_character: str
    to_character: str
    relationship_type: str
    description: str = ""
    strength: float = 0.5


class WorldBuildingCreate(BaseModel):
    name: str
    era: str = ""
    geography: str = ""
    social_structure: str = ""
    technology_level: str = ""


class OutlineGenerate(BaseModel):
    genre: str = "xuanhuan"
    title: str = "Untitled"
    summary: str = ""
    total_chapters: int = 100


class PipelineStart(BaseModel):
    start_chapter: int = 1
    end_chapter: int = 10


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

    # --- New API endpoints: Chapters, Outlines, Profiles, Pipeline ---

    # --- Chapters ---
    @app.get("/api/chapters")
    def list_chapters(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        chapters = db.list_chapters()
        return {"chapters": [ch.model_dump() for ch in chapters]}

    @app.get("/api/chapters/{chapter_num}")
    def get_chapter(chapter_num: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        ch = db.get_chapter(chapter_num)
        if ch is None:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        return ch.model_dump()

    @app.post("/api/chapters")
    def create_chapter(ch: ChapterCreate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        existing = db.list_chapters()
        next_num = max([c.chapter_num for c in existing], default=0) + 1
        chapter = Chapter(
            chapter_num=next_num,
            title=ch.title or f"Chapter {next_num}",
            content=ch.content,
        )
        db.update_chapter(chapter)
        return {"message": f"Chapter {next_num} created", "chapter": chapter.model_dump()}

    @app.put("/api/chapters/{chapter_num}")
    def update_chapter(chapter_num: int, ch: ChapterUpdate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        existing = db.get_chapter(chapter_num)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        if ch.title is not None:
            existing.title = ch.title
        if ch.content is not None:
            existing.content = ch.content
        if ch.status is not None:
            existing.status = ch.status
        existing.updated_at = datetime.now().isoformat()
        db.update_chapter(existing)
        return {"message": f"Chapter {chapter_num} updated"}

    @app.delete("/api/chapters/{chapter_num}")
    def delete_chapter(chapter_num: int, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        db.delete_chapter(chapter_num)
        return {"message": f"Chapter {chapter_num} deleted"}

    # --- Outlines ---
    @app.get("/api/outlines")
    def get_outline(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        outline = db.get_outline()
        if outline is None:
            return {"outline": None}
        return {"outline": outline.model_dump()}

    @app.post("/api/outlines/generate")
    def generate_outline(body: OutlineGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.agents.outline import OutlineAgent
        agent = OutlineAgent()
        outline = agent.run(
            genre=body.genre,
            title=body.title,
            summary=body.summary,
            total_chapters=body.total_chapters,
        )
        db.save_outline(outline)
        return {"message": "Outline generated", "outline": outline.model_dump()}

    @app.put("/api/outlines")
    def update_outline(body: OutlineGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.agents.outline import OutlineAgent
        agent = OutlineAgent()
        outline = agent.run(
            genre="xuanhuan",
            title=body.title,
            summary=body.summary,
            total_chapters=body.total_chapters,
        )
        db.save_outline(outline)
        return {"message": "Outline updated", "outline": outline.model_dump()}

    # --- Character Profiles ---
    @app.get("/api/profiles")
    def list_profiles(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        profiles = db.list_character_profiles()
        return {"profiles": [p.model_dump() for p in profiles]}

    @app.get("/api/profiles/{name}")
    def get_profile(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        profile = db.get_character_profile(name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
        return profile.model_dump()

    @app.post("/api/profiles")
    def create_profile(body: ProfileCreate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        profile = CharacterProfile(
            name=body.name,
            gender=body.gender,
            age=body.age,
            appearance=body.appearance,
            personality=body.personality,
            backstory=body.backstory,
            motivation=body.motivation,
            voice_profile_ref=body.voice_profile_ref,
        )
        db.save_character_profile(profile)
        return {"message": f"Profile '{body.name}' created"}

    @app.put("/api/profiles/{name}")
    def update_profile(name: str, body: ProfileUpdate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        existing = db.get_character_profile(name)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
        if body.gender is not None:
            existing.gender = body.gender
        if body.age is not None:
            existing.age = body.age
        if body.appearance is not None:
            existing.appearance = body.appearance
        if body.personality is not None:
            existing.personality = body.personality
        if body.backstory is not None:
            existing.backstory = body.backstory
        if body.motivation is not None:
            existing.motivation = body.motivation
        if body.voice_profile_ref is not None:
            existing.voice_profile_ref = body.voice_profile_ref
        db.save_character_profile(existing)
        return {"message": f"Profile '{name}' updated"}

    @app.delete("/api/profiles/{name}")
    def delete_profile(name: str, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        # Soft delete: just remove from profiles table
        db.conn.execute("DELETE FROM character_profiles WHERE name = ?", (name,))
        db.conn.commit()
        return {"message": f"Profile '{name}' deleted"}

    # --- Character Relationships ---
    @app.get("/api/relationships")
    def list_relationships(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        rels = db.list_all_relationships()
        return {"relationships": [r.model_dump() for r in rels]}

    @app.post("/api/relationships")
    def create_relationship(body: RelationshipCreate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        rel = CharacterRelationship(
            from_character=body.from_character,
            to_character=body.to_character,
            relationship_type=body.relationship_type,
            description=body.description,
            strength=body.strength,
        )
        db.add_character_relationship(rel)
        return {"message": "Relationship created"}

    # --- World Building ---
    @app.get("/api/world-building")
    def get_world_building(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        wb = db.get_world_building()
        if wb is None:
            return {"world_building": None}
        return {"world_building": wb.model_dump()}

    @app.post("/api/world-building")
    def create_world_building(body: WorldBuildingCreate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        wb = WorldBuilding(
            name=body.name,
            era=body.era,
            geography=body.geography,
            social_structure=body.social_structure,
            technology_level=body.technology_level,
        )
        db.save_world_building(wb)
        return {"message": "World building saved"}

    @app.put("/api/world-building")
    def update_world_building(body: WorldBuildingCreate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        wb = WorldBuilding(
            name=body.name,
            era=body.era,
            geography=body.geography,
            social_structure=body.social_structure,
            technology_level=body.technology_level,
        )
        db.save_world_building(wb)
        return {"message": "World building updated"}

    # --- Power Systems ---
    @app.get("/api/power-systems")
    def list_power_systems(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        systems = db.get_power_systems()
        return {"power_systems": [s.model_dump() for s in systems]}

    @app.post("/api/power-systems")
    def create_power_system(body: Dict[str, Any], db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        ps = PowerSystem(
            name=body.get("name", ""),
            levels=body.get("levels", []),
            rules=body.get("rules", ""),
        )
        db.add_power_system(ps)
        return {"message": "Power system created"}

    # --- Timeline ---
    @app.get("/api/timeline")
    def get_timeline(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        events = db.get_timeline()
        return {"timeline": [e.model_dump() for e in events]}

    @app.post("/api/timeline")
    def create_timeline_event(body: Dict[str, Any], db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        tl = Timeline(
            year=body.get("year", 0),
            event=body.get("event", ""),
            impact=body.get("impact", ""),
        )
        db.add_timeline_event(tl)
        return {"message": "Timeline event created"}

    # --- Pipeline Control ---
    @app.post("/api/pipeline/run-chapter/{chapter_num}")
    def run_chapter(chapter_num: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.core.orchestrator import PipelineOrchestrator
        orb = PipelineOrchestrator(state_db=db)
        result = orb.run_chapter(chapter_num)
        return result

    @app.post("/api/pipeline/run-batch")
    def run_batch(body: PipelineStart, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.core.orchestrator import PipelineOrchestrator
        orb = PipelineOrchestrator(state_db=db)
        results = orb.run_batch(start=body.start_chapter, end=body.end_chapter)
        return {"results": {str(k): v for k, v in results.items()}}

    @app.get("/api/pipeline/status")
    def pipeline_status(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.core.orchestrator import PipelineOrchestrator
        orb = PipelineOrchestrator(state_db=db)
        return orb.status

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
