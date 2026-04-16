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


class ExportRequest(BaseModel):
    format: str = "txt"  # "txt", "md", "html"


class ConfigSave(BaseModel):
    """Configuration save request."""
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    default_model: Optional[str] = None
    writer_model: Optional[str] = None
    editor_model: Optional[str] = None
    redteam_model: Optional[str] = None
    navigator_model: Optional[str] = None
    director_model: Optional[str] = None
    review_mode: Optional[str] = None
    max_retries: Optional[int] = None
    pipeline_parallel: Optional[bool] = None


# --- Phase 3 models ---

class ImportTextRequest(BaseModel):
    title: str = "Untitled"
    content: str = ""


class ImportApplyRequest(BaseModel):
    title: str = "Untitled"
    content: str = ""


class SideStoryGenerate(BaseModel):
    characters: List[str] = []
    setting: str = ""
    topic: str = ""


class ImitationGenerate(BaseModel):
    sample_text: str = ""
    topic: str = ""


class StyleExtractRequest(BaseModel):
    text: str = ""


class DaemonStartRequest(BaseModel):
    start_chapter: int = 1
    end_chapter: int = 10
    interval_seconds: int = 60


class PipelineManager:
    """Singleton that owns the running PipelineOrchestrator and its background task.

    Solves the bug where each API endpoint created a new orchestrator instance,
    making pause/resume/stop operate on a different object than the running pipeline.
    """

    def __init__(self):
        self._orchestrator: Optional[Any] = None  # PipelineOrchestrator
        self._task: Optional[asyncio.Task] = None
        self._db: Optional[StateDB] = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _create_orchestrator(self, db: StateDB) -> Any:
        """Create a new PipelineOrchestrator with current config."""
        from Engine.core.orchestrator import PipelineOrchestrator
        from Engine.core.memory_bank import MemoryBank
        config = _get_engine_config(db)

        # Get review_mode from config
        review_mode = "strict"
        try:
            cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
            row = cursor.fetchone()
            if row:
                db_config = json.loads(row[0])
                review_mode = db_config.get("review_mode", "strict")
        except Exception:
            pass

        # Create MemoryBank (uses ChromaDB if available, else in-memory)
        memory_bank = MemoryBank(collection_name="novel_memory")

        return PipelineOrchestrator(
            state_db=db,
            config=config,
            memory_bank=memory_bank,
            review_policy=review_mode,
        )

    async def start_chapter(self, chapter_num: int, db: StateDB) -> Dict[str, Any]:
        """Start generating a single chapter in the background."""
        if self.is_running:
            return {"error": "Pipeline already running", "started": False}
        self._db = db
        self._orchestrator = self._create_orchestrator(db)

        async def _run():
            try:
                await self._orchestrator.run_chapter(chapter_num)
            except Exception:
                pass  # Events published inside orchestrator

        self._task = asyncio.create_task(_run())
        return {"started": True, "chapter_num": chapter_num}

    async def run_chapter_sync(self, chapter_num: int, db: StateDB) -> Dict[str, Any]:
        """Run a chapter synchronously and wait for completion."""
        if self.is_running:
            return {"error": "Pipeline already running"}
        self._db = db
        self._orchestrator = self._create_orchestrator(db)

        try:
            await self._orchestrator.run_chapter(chapter_num)
            # Get the chapter result from StateDB
            ch = db.get_chapter(chapter_num)
            return {
                "chapter_num": chapter_num,
                "status": ch.status if ch else "unknown",
            }
        except Exception as e:
            return {"chapter_num": chapter_num, "status": "failed", "error": str(e)}

    async def start_batch(self, start: int, end: int, db: StateDB) -> Dict[str, Any]:
        """Start batch generation in the background."""
        if self.is_running:
            return {"error": "Pipeline already running", "started": False}
        self._db = db
        self._orchestrator = self._create_orchestrator(db)

        async def _run():
            try:
                await self._orchestrator.run_batch(start, end)
            except Exception:
                pass

        self._task = asyncio.create_task(_run())
        return {"started": True, "start": start, "end": end}

    async def run_batch_sync(self, start: int, end: int, db: StateDB) -> Dict[str, Any]:
        """Run batch synchronously and wait for completion."""
        if self.is_running:
            return {"error": "Pipeline already running"}
        self._db = db
        self._orchestrator = self._create_orchestrator(db)

        try:
            results = await self._orchestrator.run_batch(start, end)
            return {"results": {str(k): v for k, v in results.items()}}
        except Exception as e:
            return {"error": str(e)}

    def pause(self) -> Dict[str, str]:
        if self._orchestrator:
            self._orchestrator.pause()
            return {"message": "Pipeline paused"}
        return {"message": "No pipeline running"}

    def resume(self) -> Dict[str, str]:
        if self._orchestrator:
            self._orchestrator.resume()
            return {"message": "Pipeline resumed"}
        return {"message": "No pipeline running"}

    def stop(self) -> Dict[str, str]:
        if self._orchestrator:
            self._orchestrator.stop()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._orchestrator = None
        return {"message": "Pipeline stopped"}

    def get_status(self) -> Dict[str, Any]:
        if self._orchestrator:
            status = self._orchestrator.status
            status["task_alive"] = self.is_running
            return status
        return {"running": False, "paused": False, "task_alive": False}


# Global singleton
_pipeline_manager = PipelineManager()

# Project manager singleton
from Engine.core.project_manager import ProjectManager
_project_manager = ProjectManager()

# Token tracker singleton (initialized with db in lifespan)
_token_tracker: Optional[TokenTracker] = None


def _get_token_tracker() -> "TokenTracker":
    from Engine.core.token_tracker import TokenTracker
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker()
    return _token_tracker


def _init_token_tracker(db: StateDB) -> None:
    global _token_tracker
    from Engine.core.token_tracker import TokenTracker
    _token_tracker = TokenTracker(state_db=db)


def _get_db(request: Request) -> StateDB:
    """Dependency injection for StateDB."""
    return request.app.state.db


def _get_engine_config(db: StateDB):
    """Build EngineConfig from database-stored config + environment.

    Returns EngineConfig if API key is available, otherwise None (fallback to mock).
    """
    import json as _json

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    default_model = os.getenv("DEFAULT_MODEL", "qwen-plus")

    # Try to override with DB-stored config
    try:
        cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
        row = cursor.fetchone()
        if row:
            db_config = _json.loads(row[0])
            if db_config.get("llm_api_key") and db_config["llm_api_key"] != os.getenv("LLM_API_KEY", ""):
                # Use DB-stored key if different from env
                api_key = db_config["llm_api_key"]
            if db_config.get("llm_base_url"):
                base_url = db_config["llm_base_url"]
            if db_config.get("default_model"):
                default_model = db_config["default_model"]
    except Exception:
        pass

    if not api_key:
        return None

    from Engine.config import EngineConfig, LLMConfig

    llm = LLMConfig(api_key=api_key, base_url=base_url, default_model=default_model)

    role_models = {}
    for role in ("writer", "editor", "redteam", "navigator", "director"):
        env_key = f"{role.upper()}_MODEL"
        role_models[role] = os.getenv(env_key, default_model)

    return EngineConfig(llm=llm, role_models=role_models)


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


def create_app(seed_data: bool = True, db_path: str | None = None) -> FastAPI:
    """Create and configure the Studio FastAPI application.

    Args:
        seed_data: Whether to seed sample data.
        db_path: Database path. Defaults to env INKFOUNDRY_DB_PATH or 'state.db'.
                 Use ':memory:' for testing.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle with proper resource cleanup."""
        resolved_db_path = db_path if db_path is not None else os.environ.get("INKFOUNDRY_DB_PATH", "state.db")
        db = StateDB(resolved_db_path)
        app.state.db = db
        if seed_data:
            _seed_sample_data(db)
        _init_token_tracker(db)
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

    # --- Configuration Center ---
    @app.get("/api/config")
    def get_config(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Get current configuration from database."""
        import os
        # Try to get from env first
        config = {
            "llm_api_key": os.getenv("LLM_API_KEY", ""),
            "llm_base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            "default_model": os.getenv("DEFAULT_MODEL", "qwen-plus"),
            "writer_model": os.getenv("WRITER_MODEL", ""),
            "editor_model": os.getenv("EDITOR_MODEL", ""),
            "redteam_model": os.getenv("REDTEAM_MODEL", ""),
            "navigator_model": os.getenv("NAVIGATOR_MODEL", ""),
            "director_model": os.getenv("DIRECTOR_MODEL", ""),
            "review_mode": "strict",
            "max_retries": 3,
            "pipeline_parallel": False,
        }
        # Override with DB-stored values if they exist
        try:
            cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
            row = cursor.fetchone()
            if row:
                db_config = json.loads(row[0])
                config.update(db_config)
        except Exception:
            pass  # No config stored yet
        # Mask API key for security (show last 4 chars)
        if config["llm_api_key"] and len(config["llm_api_key"]) > 8:
            config["llm_api_key_masked"] = "****" + config["llm_api_key"][-4:]
        return config

    @app.post("/api/config")
    def save_config(body: ConfigSave, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Save configuration to database."""
        import os
        # Get existing config
        existing_config = {}
        try:
            cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
            row = cursor.fetchone()
            if row:
                existing_config = json.loads(row[0])
        except Exception:
            pass

        # Update config with new values
        new_config = existing_config.copy()
        for field_name in body.model_fields_set:
            value = getattr(body, field_name)
            if value is not None:
                new_config[field_name] = value

        # Store in database
        db.conn.execute(
            "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
            ("config", json.dumps(new_config)),
        )
        db.conn.commit()

        # Also update environment for current session
        if body.llm_api_key:
            os.environ["LLM_API_KEY"] = body.llm_api_key
        if body.llm_base_url:
            os.environ["LLM_BASE_URL"] = body.llm_base_url
        if body.default_model:
            os.environ["DEFAULT_MODEL"] = body.default_model

        return {"message": "Configuration saved"}

    @app.delete("/api/config")
    def delete_config(db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Delete all configuration from database."""
        db.conn.execute("DELETE FROM state WHERE key = 'config'")
        db.conn.commit()
        return {"message": "Configuration deleted"}

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

        import json
        from collections import deque
        from Engine.core.event_bus import (
            get_event_bus,
            EVENT_PIPELINE_PROGRESS,
            EVENT_CHAPTER_COMPLETE,
            EVENT_CHAPTER_FAILED,
        )

        event_queue: deque = deque()

        def _on_event(data: dict):
            event_queue.append(data)

        bus = get_event_bus()
        token_progress = bus.subscribe(EVENT_PIPELINE_PROGRESS, _on_event)
        token_complete = bus.subscribe(EVENT_CHAPTER_COMPLETE, _on_event)
        token_failed = bus.subscribe(EVENT_CHAPTER_FAILED, _on_event)

        try:
            while True:
                # Flush queued events from EventBus
                while event_queue:
                    event_data = event_queue.popleft()
                    await websocket.send_json({"type": "event", "data": event_data})

                # Process incoming client messages (non-blocking check)
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                        continue

                    action = msg.get("action", "")
                    if action == "subscribe":
                        await websocket.send_json({"type": "subscription_confirmed"})
                    elif action == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif action == "unsubscribe":
                        break
                    else:
                        await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})
                except asyncio.TimeoutError:
                    pass
        except Exception:
            pass
        finally:
            bus.unsubscribe(token_progress)
            bus.unsubscribe(token_complete)
            bus.unsubscribe(token_failed)
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
    async def generate_outline(body: OutlineGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.agents.outline import OutlineAgent
        config = _get_engine_config(db)
        agent = OutlineAgent()
        if config and config.llm.api_key:
            agent = OutlineAgent(
                model_name=config.role_models.get("navigator", config.llm.default_model),
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
            )
            outline = await agent.arun(
                genre=body.genre,
                title=body.title,
                summary=body.summary,
                total_chapters=body.total_chapters,
            )
        else:
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
    async def run_chapter(chapter_num: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Run a single chapter and wait for completion."""
        return await _pipeline_manager.run_chapter_sync(chapter_num, db)

    # --- Review ---
    @app.post("/api/review/approve/{chapter_num}")
    def approve_chapter(chapter_num: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Approve a chapter — set status to 'final'."""
        ch = db.get_chapter(chapter_num)
        if ch is None:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        ch.status = "final"
        ch.updated_at = datetime.now().isoformat()
        db.update_chapter(ch)
        return {"message": f"Chapter {chapter_num} approved"}

    @app.post("/api/review/reject/{chapter_num}")
    def reject_chapter(chapter_num: int, body: Dict[str, Any], db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Reject a chapter — set status to 'draft' with review note."""
        ch = db.get_chapter(chapter_num)
        if ch is None:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        ch.status = "draft"
        note = body.get("note", "")
        if note:
            ch.review_notes = f"{ch.review_notes or ''}\n审核拒绝: {note}"
        ch.updated_at = datetime.now().isoformat()
        db.update_chapter(ch)
        return {"message": f"Chapter {chapter_num} rejected"}

    @app.post("/api/pipeline/run-batch")
    async def run_batch(body: PipelineStart, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Run batch and wait for completion."""
        return await _pipeline_manager.run_batch_sync(body.start_chapter, body.end_chapter, db)

    @app.get("/api/pipeline/status")
    def pipeline_status() -> Dict[str, Any]:
        """Get current pipeline status."""
        return _pipeline_manager.get_status()

    @app.post("/api/pipeline/pause")
    def pipeline_pause() -> Dict[str, str]:
        """Pause the pipeline."""
        return _pipeline_manager.pause()

    @app.post("/api/pipeline/resume")
    def pipeline_resume() -> Dict[str, str]:
        """Resume the pipeline."""
        return _pipeline_manager.resume()

    @app.post("/api/pipeline/stop")
    def pipeline_stop() -> Dict[str, str]:
        """Stop the pipeline."""
        return _pipeline_manager.stop()

    # --- Novel Export ---
    @app.post("/api/export")
    def export_novel(body: ExportRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Export novel to txt, md, or html format."""
        import tempfile
        from Engine.core.exporter import NovelExporter

        if body.format not in ("txt", "md", "html"):
            raise HTTPException(status_code=400, detail="Unsupported format. Use: txt, md, html")

        # Get outline for title
        outline = db.get_outline()
        title = outline.title if outline else "Untitled Novel"

        # Get all chapters
        chapters = db.list_chapters()
        if not chapters:
            raise HTTPException(status_code=404, detail="No chapters to export")

        novel_data = {
            "title": title,
            "chapters": [
                {"number": ch.chapter_num, "content": ch.content, "title": ch.title}
                for ch in sorted(chapters, key=lambda c: c.chapter_num)
            ],
        }

        # Export to temp file
        ext = body.format if body.format != "html" else "html"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f".{ext}", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name

        try:
            if body.format == "txt":
                NovelExporter.to_txt(novel_data, tmp_path)
            elif body.format == "md":
                NovelExporter.to_markdown(novel_data, tmp_path)
            elif body.format == "html":
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(NovelExporter._to_html(novel_data))

            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            filename = f"{title}.{ext}"
            return {"content": content, "filename": filename}
        finally:
            os.unlink(tmp_path)

    # --- Project Management ---
    class ProjectCreate(BaseModel):
        title: str
        genre: str = "unknown"

    @app.get("/api/projects")
    def list_projects() -> Dict[str, Any]:
        """List all active projects."""
        projects = _project_manager.list_projects(status="active")
        return {"projects": [p.__dict__ for p in projects]}

    @app.post("/api/projects")
    def create_project(body: ProjectCreate) -> Dict[str, Any]:
        """Create a new project."""
        info = _project_manager.create_project(title=body.title, genre=body.genre)
        return {"message": f"Project '{body.title}' created", "project": info.__dict__}

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> Dict[str, Any]:
        """Get project details."""
        info = _project_manager.get_project(project_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return {"project": info.__dict__}

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str) -> Dict[str, str]:
        """Soft-delete a project."""
        success = _project_manager.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return {"message": f"Project '{project_id}' deleted"}

    @app.post("/api/projects/{project_id}/activate")
    def activate_project(project_id: str, request: Request) -> Dict[str, str]:
        """Switch to a different project — updates the active DB."""
        info = _project_manager.get_project(project_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Swap the DB on the app state
        from Engine.core.state_db import StateDB
        old_db = request.app.state.db
        if old_db:
            old_db.close()

        new_db = StateDB(info.db_path)
        request.app.state.db = new_db
        request.app.state.current_project_id = project_id

        return {"message": f"Switched to project '{info.title}'"}

    # --- Token Stats ---
    @app.get("/api/token-stats")
    def get_token_stats() -> Dict[str, Any]:
        """Get aggregated token usage statistics."""
        tracker = _get_token_tracker()
        stats = tracker.stats
        return {
            "total_prompt_tokens": stats.total_prompt_tokens,
            "total_completion_tokens": stats.total_completion_tokens,
            "total_tokens": stats.total_tokens,
            "total_requests": stats.total_requests,
            "total_cost_estimate": round(stats.total_cost_estimate, 6),
            "by_model": stats.by_model,
            "by_task": stats.by_task,
        }

    @app.get("/api/token-records")
    def get_token_records() -> Dict[str, Any]:
        """Get detailed token usage records."""
        tracker = _get_token_tracker()
        records = [
            {
                "timestamp": r.timestamp,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "task": r.task,
                "cost_estimate": round(r.cost_estimate, 6),
            }
            for r in tracker.records[-100:]  # Last 100 records
        ]
        return {"records": records}

    # --- Snapshot Management ---
    @app.get("/api/snapshots")
    def list_snapshots(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """List all snapshots."""
        snaps = db.list_snapshots()
        return {"snapshots": [s.model_dump() for s in snaps]}

    @app.post("/api/snapshots")
    def save_snapshot(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Save current state as snapshot."""
        from Engine.core.models import StateSnapshot

        # Gather current state
        chars_cursor = db.conn.execute("SELECT data FROM characters")
        ws_cursor = db.conn.execute("SELECT data FROM world_states")
        chapters_cursor = db.conn.execute("SELECT data FROM chapters")

        characters = [CharacterState.model_validate_json(r[0]).model_dump() for r in chars_cursor.fetchall()]
        world_states = [{"name": "default", "description": "", "state": "normal"}]
        chapters_data = [json.loads(r[0]) for r in chapters_cursor.fetchall()]

        # Get max version
        version_row = db.conn.execute("SELECT MAX(version) FROM snapshots").fetchone()
        next_version = (version_row[0] or 0) + 1

        snapshot = StateSnapshot(
            version=next_version,
            chapter_num=chapters_data[-1].get("chapter_num", 0) if chapters_data else 0,
            data={
                "characters": characters,
                "world_states": world_states,
                "chapters": chapters_data,
            },
        )
        db.save_snapshot(snapshot)
        return {"message": f"Snapshot v{next_version} saved", "version": next_version}

    @app.post("/api/snapshots/{version}/restore")
    def restore_snapshot(version: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Restore state from a snapshot."""
        snapshot = db.load_snapshot(version)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"Snapshot v{version} not found")

        data = snapshot.data
        if "characters" in data:
            for char_data in data["characters"]:
                char = CharacterState(**char_data)
                db.update_character(char)

        return {"message": f"Restored to snapshot v{version}"}

    @app.delete("/api/snapshots/{version}")
    def delete_snapshot(version: int, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Delete a snapshot."""
        snapshot = db.load_snapshot(version)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"Snapshot v{version} not found")
        db.conn.execute("DELETE FROM snapshots WHERE version = ?", (version,))
        db.conn.commit()
        return {"message": f"Snapshot v{version} deleted"}
    api_router = []

    @app.get("/api/status")
    def api_status(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Get project status from database."""
        # Read config from database
        title = "Untitled Novel"
        genre = "fiction"
        try:
            cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
            row = cursor.fetchone()
            if row:
                cfg = json.loads(row[0])
                if cfg.get("novel_title"):
                    title = cfg["novel_title"]
                if cfg.get("genre"):
                    genre = cfg["genre"]
        except Exception:
            pass

        # Count chapters
        cursor = db.conn.execute("SELECT data FROM chapters")
        chapters = []
        for row in cursor.fetchall():
            chapters.append(json.loads(row[0]))
        total_chapters = len(chapters)
        completed = sum(1 for c in chapters if c.get("status") in ("reviewed", "final"))

        # Read outline for total chapters
        try:
            cursor = db.conn.execute("SELECT data FROM outlines LIMIT 1")
            row = cursor.fetchone()
            if row:
                outline = json.loads(row[0])
                total_chapters = max(total_chapters, outline.get("total_chapters", total_chapters))
        except Exception:
            pass

        return {
            "id": "novel-001",
            "title": title,
            "genre": genre,
            "current_chapter": completed + 1 if completed > 0 else 1,
            "total_chapters": total_chapters,
            "status": "active" if completed > 0 else "idle",
        }

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

    # --- Phase 3: Value-Add Features ---

    # --- Daemon API ---
    _daemon_scheduler: Optional[Any] = None

    @app.get("/api/daemon/status")
    def daemon_status(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Get daemon status."""
        nonlocal _daemon_scheduler
        is_running = _daemon_scheduler is not None and getattr(_daemon_scheduler, "_running", False)
        return {
            "running": is_running,
            "queue_size": getattr(_daemon_scheduler, "queue_size", 0) if is_running else 0,
        }

    @app.post("/api/daemon/start")
    def daemon_start(body: DaemonStartRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Start the background daemon for automatic chapter generation."""
        nonlocal _daemon_scheduler
        from Engine.core.daemon import DaemonScheduler

        if _daemon_scheduler is None:
            _daemon_scheduler = DaemonScheduler()
            _daemon_scheduler.start()

        # Add the generation task
        _daemon_scheduler.add_task({
            "start_chapter": body.start_chapter,
            "end_chapter": body.end_chapter,
            "interval": body.interval_seconds,
        })

        return {"started": True, "start_chapter": body.start_chapter, "end_chapter": body.end_chapter}

    @app.post("/api/daemon/stop")
    def daemon_stop() -> Dict[str, Any]:
        """Stop the background daemon."""
        nonlocal _daemon_scheduler
        if _daemon_scheduler is not None:
            _daemon_scheduler.stop()
        return {"stopped": True}

    # --- Import API ---
    @app.post("/api/import/text")
    def import_from_text(body: ImportTextRequest) -> Dict[str, Any]:
        """Parse and preview imported novel from text."""
        if not body.content.strip():
            return {"title": body.title, "chapters": []}

        from Engine.core.importer import NovelImporter
        imported = NovelImporter.from_text(body.content, title=body.title)
        return {
            "title": imported.title,
            "chapters": imported.chapters,
            "chapter_count": imported.chapter_count,
        }

    @app.post("/api/import/apply")
    def import_and_apply(body: ImportApplyRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Import novel text and save chapters to StateDB."""
        from Engine.core.importer import NovelImporter
        from Engine.core.models import Chapter

        imported = NovelImporter.from_text(body.content, title=body.title)
        saved = 0
        for ch_data in imported.chapters:
            chapter = Chapter(
                chapter_num=ch_data["number"],
                title=f"Chapter {ch_data['number']}",
                content=ch_data["content"],
                status="imported",
                word_count=len(ch_data["content"]),
            )
            db.update_chapter(chapter)
            saved += 1

        return {"imported": saved, "title": imported.title}

    # --- Side Story API ---
    @app.post("/api/side-story/generate")
    def generate_side_story(body: SideStoryGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Generate a side story (番外) based on characters and setting."""
        from Engine.agents.side_story import SideStoryAgent
        config = _get_engine_config(db)

        agent = SideStoryAgent(
            model_name=config.role_models.get("writer", config.llm.default_model) if config else "dummy",
            api_key=config.llm.api_key if config else "",
            base_url=config.llm.base_url if config else "",
        )

        if config:
            import asyncio
            return {"content": asyncio.get_event_loop().run_until_complete(
                agent.arun({"characters": body.characters, "setting": body.setting, "topic": body.topic})
            )}

        content = agent.run({
            "characters": body.characters,
            "setting": body.setting,
            "topic": body.topic,
        })
        return {"content": content}

    # --- Imitation API ---
    @app.post("/api/imitation/generate")
    def generate_imitation(body: ImitationGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Generate content imitating the style of a sample text."""
        from Engine.agents.imitation import ImitationAgent
        config = _get_engine_config(db)

        agent = ImitationAgent(
            model_name=config.role_models.get("writer", config.llm.default_model) if config else "dummy",
            api_key=config.llm.api_key if config else "",
            base_url=config.llm.base_url if config else "",
        )

        if config:
            import asyncio
            return {"content": asyncio.get_event_loop().run_until_complete(
                agent.arun({"sample_text": body.sample_text, "topic": body.topic})
            )}

        content = agent.run({
            "sample_text": body.sample_text,
            "topic": body.topic,
        })
        return {"content": content}

    # --- Style API ---
    @app.post("/api/style/extract")
    def extract_style(body: StyleExtractRequest) -> Dict[str, Any]:
        """Extract style features from provided text."""
        from Engine.llm.style_extractor import StyleExtractor

        profile = StyleExtractor.extract(body.text)
        return {
            "avg_sentence_length": profile.avg_sentence_length,
            "avg_paragraph_length": profile.avg_paragraph_length,
            "vocabulary_richness": profile.vocabulary_richness,
            "common_patterns": profile.common_patterns,
            "tone": profile.tone,
        }

    @app.post("/api/style/fingerprint")
    def style_fingerprint(body: StyleExtractRequest) -> Dict[str, Any]:
        """Generate a style fingerprint for the provided text."""
        from Engine.llm.style_extractor import StyleExtractor

        profile = StyleExtractor.extract(body.text)
        fingerprint = (
            f"{profile.avg_sentence_length:.1f}_{profile.tone}_"
            f"{'-'.join(profile.common_patterns[:3])}"
        )
        return {
            "fingerprint": fingerprint,
            "style_profile": {
                "avg_sentence_length": profile.avg_sentence_length,
                "avg_paragraph_length": profile.avg_paragraph_length,
                "vocabulary_richness": profile.vocabulary_richness,
                "common_patterns": profile.common_patterns,
                "tone": profile.tone,
            },
        }

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
