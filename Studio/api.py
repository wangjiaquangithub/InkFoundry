"""Studio FastAPI backend - REST API for the UI dashboard."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from Engine.config import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    ROLE_NAMES,
    EngineConfig,
    InvalidLLMConfigError,
    LLMConfig,
    normalize_base_url,
    normalize_model_name,
    validate_llm_settings,
)
from Engine.core.state_db import StateDB
from Engine.core.models import (
    CharacterState, Chapter, Outline, CharacterProfile,
    CharacterRelationship, WorldBuilding, PowerSystem, Timeline,
    StateSnapshot, WorldState,
)

logger = logging.getLogger(__name__)


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


class CoreChainReadiness(BaseModel):
    project_brief_ready: bool = False
    outline_ready: bool = False
    real_model_ready: bool = False
    chapter_ready: bool = False


class ProjectStatus(BaseModel):
    id: str = "novel-001"
    title: str = "Untitled Novel"
    genre: str = "fiction"
    current_chapter: int = 1
    total_chapters: int = 10
    status: str = "idle"
    core_chain_readiness: CoreChainReadiness = CoreChainReadiness()


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
    genre: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    total_chapters: Optional[int] = None


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


class AIDetectRequest(BaseModel):
    text: str = ""


class TrendAnalyzeRequest(BaseModel):
    genre: str = ""
    keywords: List[str] = []


class ProjectCreate(BaseModel):
    title: str
    genre: str = "unknown"
    summary: str = ""
    target_chapters: int = 100


class ReviewRejectRequest(BaseModel):
    note: str = ""


@dataclass
class PipelineRuntime:
    db: Optional[StateDB] = None
    orchestrator: Optional[Any] = None
    task: Optional[asyncio.Task] = None
    sync_run_lock: threading.Lock = field(default_factory=threading.Lock)
    sync_running: bool = False


class PipelineManager:
    """Singleton that owns the running PipelineOrchestrator and its background task.

    Solves the bug where each API endpoint created a new orchestrator instance,
    making pause/resume/stop operate on a different object than the running pipeline.
    """

    def __init__(self):
        self._runtimes: Dict[str, PipelineRuntime] = {}
        self._registry_lock = threading.Lock()

    def _memory_scope(self, db: StateDB) -> tuple[str, Optional[str]]:
        project_key = getattr(db, "db_path", "") or "__default__"
        if project_key == ":memory:":
            return f":memory:{id(db)}", None
        return project_key, f"{project_key}.memory"

    def _project_key(self, db: StateDB) -> str:
        return self._memory_scope(db)[0]

    def _runtime_for_db(self, db: StateDB) -> PipelineRuntime:
        project_key = self._project_key(db)
        with self._registry_lock:
            runtime = self._runtimes.get(project_key)
            if runtime is None:
                runtime = PipelineRuntime(db=db)
                self._runtimes[project_key] = runtime
            elif runtime.db is None:
                runtime.db = db
            return runtime

    def _is_runtime_running(self, runtime: PipelineRuntime) -> bool:
        return runtime.sync_running or (runtime.task is not None and not runtime.task.done())

    def _clear_runtime(self, db: StateDB) -> None:
        project_key = self._project_key(db)
        with self._registry_lock:
            runtime = self._runtimes.get(project_key)
            if runtime is None:
                return
            runtime.task = None
            runtime.orchestrator = None
            runtime.db = None
            runtime.sync_running = False
            self._runtimes.pop(project_key, None)

    @property
    def is_running(self) -> bool:
        with self._registry_lock:
            return any(self._is_runtime_running(runtime) for runtime in self._runtimes.values())

    def _create_orchestrator(self, db: StateDB) -> Any:
        """Create a new PipelineOrchestrator with current config."""
        import json
        from Engine.core.orchestrator import PipelineOrchestrator
        from Engine.core.memory_bank import MemoryBank
        config = _get_engine_config_or_http(db)

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

        memory_scope, persist_directory = self._memory_scope(db)
        project_hash = hashlib.md5(memory_scope.encode("utf-8")).hexdigest()[:12]
        memory_bank = MemoryBank(
            collection_name=f"novel_memory_{project_hash}",
            persist_directory=persist_directory,
        )

        return PipelineOrchestrator(
            state_db=db,
            config=config,
            memory_bank=memory_bank,
            review_policy=review_mode,
        )

    async def start_chapter(self, chapter_num: int, db: StateDB) -> Dict[str, Any]:
        """Start generating a single chapter in the background."""
        runtime = self._runtime_for_db(db)
        if not runtime.sync_run_lock.acquire(blocking=False):
            return {"error": "Pipeline already running", "started": False}

        try:
            if self._is_runtime_running(runtime):
                return {"error": "Pipeline already running", "started": False}
            runtime.db = db
            runtime.orchestrator = self._create_orchestrator(db)

            async def _run():
                try:
                    await runtime.orchestrator.run_chapter(chapter_num)
                except Exception:
                    pass  # Events published inside orchestrator
                finally:
                    self._clear_runtime(db)

            runtime.task = asyncio.create_task(_run())
            return {"started": True, "chapter_num": chapter_num}
        finally:
            runtime.sync_run_lock.release()

    async def run_chapter_sync(self, chapter_num: int, db: StateDB) -> Dict[str, Any]:
        """Run a chapter synchronously and wait for completion."""
        runtime = self._runtime_for_db(db)
        if self._is_runtime_running(runtime) or not runtime.sync_run_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Pipeline already running")

        orchestrator: Optional[Any] = None
        try:
            orchestrator = self._create_orchestrator(db)
            runtime.db = db
            runtime.orchestrator = orchestrator
            runtime.sync_running = True

            result = await orchestrator.run_chapter(chapter_num)
            ch = db.get_chapter(chapter_num)
            status_from_result = result.get("status", "unknown") if isinstance(result, dict) else "unknown"
            return {
                "chapter_num": chapter_num,
                "status": ch.status if ch else status_from_result,
                "mode": "model" if hasattr(orchestrator, "_has_api_key") and orchestrator._has_api_key() else "fallback",
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Chapter generation failed for chapter %s (type=%s)",
                chapter_num,
                type(exc).__name__,
            )
            raise HTTPException(status_code=500, detail="Chapter generation failed") from exc
        finally:
            runtime.sync_running = False
            runtime.task = None
            runtime.orchestrator = None
            runtime.db = None
            runtime.sync_run_lock.release()
            self._clear_runtime(db)

    async def start_batch(self, start: int, end: int, db: StateDB) -> Dict[str, Any]:
        """Start batch generation in the background."""
        runtime = self._runtime_for_db(db)
        if not runtime.sync_run_lock.acquire(blocking=False):
            return {"error": "Pipeline already running", "started": False}

        try:
            if self._is_runtime_running(runtime):
                return {"error": "Pipeline already running", "started": False}
            runtime.db = db
            runtime.orchestrator = self._create_orchestrator(db)

            async def _run():
                try:
                    await runtime.orchestrator.run_batch(start, end)
                except Exception:
                    pass
                finally:
                    self._clear_runtime(db)

            runtime.task = asyncio.create_task(_run())
            return {"started": True, "start": start, "end": end}
        finally:
            runtime.sync_run_lock.release()

    async def run_batch_sync(self, start: int, end: int, db: StateDB) -> Dict[str, Any]:
        """Run batch synchronously and wait for completion."""
        runtime = self._runtime_for_db(db)
        if self._is_runtime_running(runtime) or not runtime.sync_run_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Pipeline already running")

        orchestrator: Optional[Any] = None
        try:
            orchestrator = self._create_orchestrator(db)
            runtime.db = db
            runtime.orchestrator = orchestrator
            runtime.sync_running = True

            results = await orchestrator.run_batch(start, end)
            return {"results": {str(k): v for k, v in results.items()}}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Batch generation failed for chapters %s-%s (type=%s)",
                start,
                end,
                type(exc).__name__,
            )
            raise HTTPException(status_code=500, detail="Batch generation failed") from exc
        finally:
            runtime.sync_running = False
            runtime.task = None
            runtime.orchestrator = None
            runtime.db = None
            runtime.sync_run_lock.release()
            self._clear_runtime(db)

    def pause(self, db: StateDB) -> Dict[str, str]:
        runtime = self._runtimes.get(self._project_key(db))
        if runtime and runtime.orchestrator:
            runtime.orchestrator.pause()
            return {"message": "Pipeline paused"}
        return {"message": "No pipeline running"}

    def resume(self, db: StateDB) -> Dict[str, str]:
        runtime = self._runtimes.get(self._project_key(db))
        if runtime and runtime.orchestrator:
            runtime.orchestrator.resume()
            return {"message": "Pipeline resumed"}
        return {"message": "No pipeline running"}

    def stop(self, db: StateDB) -> Dict[str, str]:
        runtime = self._runtimes.get(self._project_key(db))
        if runtime is None:
            return {"message": "No pipeline running"}
        stop_orchestrator = getattr(runtime.orchestrator, "stop", None)
        if callable(stop_orchestrator):
            stop_orchestrator()
        if runtime.task and not runtime.task.done():
            runtime.task.cancel()
        self._clear_runtime(db)
        return {"message": "Pipeline stopped"}

    def get_status(self, db: Optional[StateDB] = None) -> Dict[str, Any]:
        if db is None:
            return {"running": False, "paused": False, "task_alive": False}
        runtime = self._runtimes.get(self._project_key(db))
        if runtime is None or runtime.orchestrator is None:
            return {"running": False, "paused": False, "task_alive": False}
        status = dict(runtime.orchestrator.status)
        status["task_alive"] = self._is_runtime_running(runtime)
        return status


from Engine.core.project_manager import ProjectInfo, ProjectManager

ACTIVE_PROJECT_COOKIE = "inkfoundry_active_project_id"


# Token tracker singleton (initialized with db in lifespan)
_token_tracker: Optional[TokenTracker] = None


def _get_token_tracker(db: Optional[StateDB] = None) -> "TokenTracker":
    from Engine.core.token_tracker import TokenTracker
    global _token_tracker
    if db is None:
        if _token_tracker is None:
            _token_tracker = TokenTracker()
        return _token_tracker

    if _token_tracker is None or getattr(_token_tracker, "_state_db", None) is not db:
        _token_tracker = TokenTracker(state_db=db)
    return _token_tracker


def _init_token_tracker(db: StateDB) -> None:
    global _token_tracker
    from Engine.core.token_tracker import TokenTracker
    _token_tracker = TokenTracker(state_db=db)


def _resolve_active_project_id(request: Request) -> Optional[str]:
    project_id = request.cookies.get(ACTIVE_PROJECT_COOKIE)
    if not project_id:
        return None
    project_id = project_id.strip()
    return project_id or None


def _should_use_secure_cookie(request: Request) -> bool:
    return request.url.scheme == "https"


def _build_clear_active_project_cookie_header(request: Request) -> str:
    secure = _should_use_secure_cookie(request)
    response = Response()
    response.delete_cookie(
        ACTIVE_PROJECT_COOKIE,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    header = response.headers.get("set-cookie")
    if header:
        return header
    secure_suffix = "; Secure" if secure else ""
    return f"{ACTIVE_PROJECT_COOKIE}=; Max-Age=0; Path=/; SameSite=lax; HttpOnly{secure_suffix}"


def _raise_inactive_project_selection(request: Request) -> None:
    raise HTTPException(
        status_code=409,
        detail="Active project is no longer available; please reselect a project",
        headers={"set-cookie": _build_clear_active_project_cookie_header(request)},
    )


def _open_project_db(db_path: str) -> Iterator[StateDB]:
    db = StateDB(db_path)
    try:
        yield db
    finally:
        db.close()


def _get_db(request: Request, response: Response) -> Iterator[StateDB]:
    """Dependency injection for request-scoped StateDB."""
    project_manager = _get_project_manager(request)
    project_id = _resolve_active_project_id(request)
    if not project_id:
        yield request.app.state.db
        return

    info = _get_active_catalog_project(project_manager, project_id)
    if info is None:
        _clear_active_project_cookie(request, response)
        _raise_inactive_project_selection(request)

    yield from _open_project_db(info.db_path)


def _get_project_manager(request: Request) -> ProjectManager:
    """Dependency injection for ProjectManager."""
    return request.app.state.project_manager


def _load_stored_config(db: StateDB) -> Dict[str, Any]:
    """Load only DB-persisted config values."""
    cursor = db.conn.execute("SELECT data FROM state WHERE key = 'config'")
    row = cursor.fetchone()
    if not row:
        return {}

    try:
        config = json.loads(row[0])
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Stored config contains invalid JSON") from exc

    if not isinstance(config, dict):
        raise HTTPException(status_code=500, detail="Stored config must be a JSON object")

    return config


def _get_effective_config(db: StateDB) -> Dict[str, Any]:
    """Merge env defaults with DB-stored configuration."""
    config = {
        "llm_api_key": os.getenv("LLM_API_KEY", ""),
        "llm_base_url": normalize_base_url(os.getenv("LLM_BASE_URL")),
        "default_model": normalize_model_name(os.getenv("DEFAULT_MODEL")),
        "review_mode": "strict",
        "max_retries": 3,
        "pipeline_parallel": False,
    }
    for role in ROLE_NAMES:
        config[f"{role}_model"] = os.getenv(f"{role.upper()}_MODEL", "")

    config.update(_load_stored_config(db))
    config["llm_base_url"] = normalize_base_url(config.get("llm_base_url"))
    config["default_model"] = normalize_model_name(config.get("default_model"))
    return config


def _validate_effective_config(config: Dict[str, Any]) -> None:
    role_models = {
        role: normalize_model_name(config.get(f"{role}_model"))
        for role in ROLE_NAMES
        if config.get(f"{role}_model")
    }
    validate_llm_settings(
        config.get("default_model", DEFAULT_LLM_MODEL),
        config.get("llm_base_url", DEFAULT_LLM_BASE_URL),
        role_models,
    )


def _get_engine_config(db: StateDB):
    """Build EngineConfig from database-stored config + environment.

    Returns EngineConfig if API key is available, otherwise None (fallback to mock).
    """
    config = _get_effective_config(db)
    api_key = config.get("llm_api_key", "")
    if not api_key:
        return None

    _validate_effective_config(config)

    llm = LLMConfig(
        api_key=api_key,
        base_url=config["llm_base_url"],
        default_model=config["default_model"],
    )
    role_models = {
        role: normalize_model_name(config.get(f"{role}_model")) if config.get(f"{role}_model") else config["default_model"]
        for role in ROLE_NAMES
    }
    return EngineConfig(llm=llm, role_models=role_models)


def _get_engine_config_or_http(db: StateDB):
    """Return EngineConfig, surfacing malformed stored config as 500 and invalid LLM settings as 422."""
    try:
        return _get_engine_config(db)
    except InvalidLLMConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _require_real_chapter_model(db: StateDB) -> EngineConfig:
    """Require a real model configuration before chapter generation."""
    config = _get_engine_config_or_http(db)
    if config is None or not config.llm.api_key:
        raise HTTPException(
            status_code=422,
            detail="A real LLM configuration is required before generating chapters",
        )
    return config


def _normalize_target_chapters(value: Optional[int], default: int = 100) -> int:
    if value is None:
        return default
    if value < 1 or value > 1000:
        raise HTTPException(status_code=422, detail="target_chapters must be between 1 and 1000")
    return value


def _get_project_brief(db: StateDB) -> Dict[str, Any]:
    brief = db.get_state("project_brief") or {}
    if not isinstance(brief, dict):
        return {}
    return brief


def _compute_core_chain_readiness(db: StateDB) -> Dict[str, bool]:
    brief = _get_project_brief(db)
    has_project_summary = bool(str(brief.get("summary") or "").strip())
    has_outline = db.get_outline() is not None

    try:
        engine_config = _get_engine_config_or_http(db)
    except HTTPException as exc:
        if exc.status_code == 422:
            has_real_model = False
        else:
            raise
    else:
        has_real_model = engine_config is not None and bool(engine_config.llm.api_key)

    return {
        "project_brief_ready": has_project_summary,
        "outline_ready": has_outline,
        "real_model_ready": has_real_model,
        "chapter_ready": has_project_summary and has_outline and has_real_model,
    }



def _safe_core_chain_readiness(db: StateDB) -> Dict[str, bool]:
    try:
        return _compute_core_chain_readiness(db)
    except Exception:
        return {
            "project_brief_ready": False,
            "outline_ready": False,
            "real_model_ready": False,
            "chapter_ready": False,
        }



def _fallback_project_status() -> Dict[str, Any]:
    return {
        "id": "novel-001",
        "title": "Untitled Novel",
        "genre": "fiction",
        "current_chapter": 1,
        "total_chapters": 10,
        "status": "error",
        "core_chain_readiness": {
            "project_brief_ready": False,
            "outline_ready": False,
            "real_model_ready": False,
            "chapter_ready": False,
        },
    }


def _derive_current_chapter(chapters: List[Dict[str, Any]], total_chapters: int) -> int:
    if total_chapters <= 0:
        return 1

    chapter_status_map = {
        int(chapter.get("chapter_num")): str(chapter.get("status") or "")
        for chapter in chapters
        if isinstance(chapter.get("chapter_num"), int)
    }
    completed_statuses = {"reviewed", "final"}

    for chapter_num in range(1, total_chapters + 1):
        if chapter_status_map.get(chapter_num) not in completed_statuses:
            return chapter_num
    return total_chapters


def _derive_project_status(completed: int, total_chapters: int, pipeline_status: Dict[str, Any]) -> str:
    if pipeline_status.get("paused"):
        return "paused"
    if pipeline_status.get("running"):
        return "running"
    if completed >= total_chapters and total_chapters > 0:
        return "completed"
    return "idle"


def _build_project_status(db: StateDB, pipeline_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    brief = _get_project_brief(db)
    config = _load_stored_config(db)
    readiness = _safe_core_chain_readiness(db)
    title = brief.get("title") or config.get("novel_title") or "Untitled Novel"
    genre = brief.get("genre") or config.get("genre") or "fiction"

    chapters = [
        {
            "chapter_num": ch.chapter_num,
            "title": ch.title,
            "content": ch.content,
            "status": ch.status,
            "word_count": ch.word_count,
            "tension_level": ch.tension_level,
            "created_at": ch.created_at,
            "updated_at": ch.updated_at,
        }
        for ch in db.list_chapters()
    ]
    total_chapters = len(chapters)
    completed = sum(1 for c in chapters if c.get("status") in ("reviewed", "final"))

    outline = db.get_outline()
    if outline:
        total_chapters = max(total_chapters, outline.total_chapters or total_chapters)
    elif brief.get("target_chapters"):
        total_chapters = max(total_chapters, _normalize_target_chapters(brief.get("target_chapters"), default=100))

    resolved_pipeline_status = pipeline_status if pipeline_status is not None else {"running": False, "paused": False, "task_alive": False}

    return {
        "id": "novel-001",
        "title": title,
        "genre": genre,
        "current_chapter": _derive_current_chapter(chapters, total_chapters),
        "total_chapters": total_chapters,
        "status": _derive_project_status(completed, total_chapters, resolved_pipeline_status),
        "core_chain_readiness": readiness,
    }


def _safe_project_status(db: StateDB, pipeline_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        return _build_project_status(db, pipeline_status=pipeline_status)
    except Exception:
        logger.exception("Failed to compute project status")
        return _fallback_project_status()


def _get_pipeline_manager(request: Request) -> PipelineManager:
    return request.app.state.pipeline_manager


def _build_project_payload(info: ProjectInfo) -> Dict[str, Any]:
    project = {
        "id": info.id,
        "title": info.title,
        "genre": info.genre,
        "created_at": info.created_at,
        "last_modified": info.last_modified,
        "status": info.status,
        "core_chain_readiness": {
            "project_brief_ready": False,
            "outline_ready": False,
            "real_model_ready": False,
            "chapter_ready": False,
        },
    }
    try:
        project_db = StateDB(info.db_path)
    except Exception:
        project.setdefault("summary", "")
        project.setdefault("target_chapters", 100)
        return project

    try:
        brief = _get_project_brief(project_db)
        project["summary"] = brief.get("summary", "")
        raw_target_chapters = brief.get("target_chapters")
        if isinstance(raw_target_chapters, int) and 1 <= raw_target_chapters <= 1000:
            project["target_chapters"] = raw_target_chapters
        else:
            project["target_chapters"] = 100

        outline = project_db.get_outline()
        chapters = project_db.list_chapters()
        project["outline_total_chapters"] = outline.total_chapters if outline else 0
        project["total_chapters"] = len(chapters)
        project["latest_chapter"] = max((c.chapter_num for c in chapters), default=0)
        project["core_chain_readiness"] = _safe_core_chain_readiness(project_db)
    finally:
        project_db.close()

    return project


def _get_active_catalog_project(project_manager: ProjectManager, project_id: str) -> Optional[ProjectInfo]:
    info = project_manager.get_project(project_id)
    if info is None or info.status != "active":
        return None
    return info


def _clear_active_project_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(
        ACTIVE_PROJECT_COOKIE,
        path="/",
        secure=_should_use_secure_cookie(request),
        httponly=True,
        samesite="lax",
    )


def _set_active_project_cookie(request: Request, response: Response, project_id: str) -> None:
    response.set_cookie(
        ACTIVE_PROJECT_COOKIE,
        project_id,
        httponly=True,
        samesite="lax",
        path="/",
        secure=_should_use_secure_cookie(request),
    )


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


def _list_character_states(db: StateDB) -> List[CharacterState]:
    cursor = db.conn.execute("SELECT data FROM characters ORDER BY name ASC")
    return [CharacterState.model_validate_json(row[0]) for row in cursor.fetchall()]


def _list_world_states(db: StateDB) -> List[WorldState]:
    cursor = db.conn.execute("SELECT data FROM world_states ORDER BY name ASC")
    return [WorldState.model_validate_json(row[0]) for row in cursor.fetchall()]


def _latest_snapshot_version(db: StateDB) -> int:
    version_row = db.conn.execute("SELECT MAX(version) FROM snapshots").fetchone()
    return version_row[0] or 0


def _require_snapshot_chapter_payload(snapshot: StateSnapshot) -> List[Dict[str, Any]]:
    chapters_data = snapshot.metadata.get("chapters")
    if chapters_data is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Snapshot v{snapshot.version} is incompatible with chapter restore; "
                "missing metadata.chapters"
            ),
        )
    if not isinstance(chapters_data, list):
        raise HTTPException(
            status_code=500,
            detail=f"Snapshot v{snapshot.version} has invalid chapter payload",
        )
    return chapters_data


def _current_chapter_num(db: StateDB) -> int:
    chapters = db.list_chapters()
    return max((chapter.chapter_num for chapter in chapters), default=0)


def _build_current_snapshot(db: StateDB, version: int = 0) -> StateSnapshot:
    with db.lock:
        db.conn.execute("BEGIN")
        try:
            chapters = db.list_chapters()
            characters = _list_character_states(db)
            world_states = _list_world_states(db)
            snapshot = StateSnapshot(
                version=version,
                chapter_num=max((chapter.chapter_num for chapter in chapters), default=0),
                characters=characters,
                world_states=world_states,
                metadata={"chapters": [chapter.model_dump() for chapter in chapters]},
            )
            db.conn.execute("COMMIT")
            return snapshot
        except Exception:
            db.conn.execute("ROLLBACK")
            raise


def _serialize_agent_results(agent_results: Any) -> str:
    if isinstance(agent_results, str):
        try:
            json.loads(agent_results)
            return agent_results
        except json.JSONDecodeError:
            return json.dumps(agent_results)
    return json.dumps(agent_results)


def _restore_snapshot_state(db: StateDB, snapshot: StateSnapshot) -> None:
    chapters_data = _require_snapshot_chapter_payload(snapshot)
    chapters = [Chapter.model_validate(chapter_data) for chapter_data in chapters_data]

    with db.lock:
        with db.conn:
            db.conn.execute("DELETE FROM characters")
            for character in snapshot.characters:
                db.conn.execute(
                    "INSERT OR REPLACE INTO characters (name, data) VALUES (?, ?)",
                    (character.name, character.model_dump_json()),
                )

            db.conn.execute("DELETE FROM world_states")
            for world_state in snapshot.world_states:
                db.conn.execute(
                    "INSERT OR REPLACE INTO world_states (name, data) VALUES (?, ?)",
                    (world_state.name, world_state.model_dump_json()),
                )

            db.conn.execute("DELETE FROM chapters")
            for chapter in chapters:
                db.conn.execute(
                    """INSERT OR REPLACE INTO chapters
                       (chapter_num, title, content, status, word_count,
                        tension_level, version, review_notes, agent_results,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chapter.chapter_num,
                        chapter.title,
                        chapter.content,
                        chapter.status,
                        chapter.word_count,
                        chapter.tension_level,
                        chapter.version,
                        chapter.review_notes,
                        _serialize_agent_results(chapter.agent_results),
                        chapter.created_at,
                        chapter.updated_at,
                    ),
                )


def _current_state_snapshot_response(db: StateDB) -> StateSnapshotResponse:
    characters = _list_character_states(db)
    world_states = _list_world_states(db)
    return StateSnapshotResponse(
        version=_latest_snapshot_version(db),
        chapter_num=_current_chapter_num(db),
        characters=[character.model_dump() for character in characters],
        world_states=[world_state.model_dump() for world_state in world_states],
    )


def create_app(
    seed_data: bool = False,
    db_path: str | None = None,
    projects_dir: str | None = None,
) -> FastAPI:
    """Create and configure the Studio FastAPI application.

    Args:
        seed_data: Whether to seed sample data.
        db_path: Database path. Defaults to env INKFOUNDRY_DB_PATH or 'state.db'.
                 Use ':memory:' for testing.
        projects_dir: Project catalog directory. Defaults to env INKFOUNDRY_PROJECTS_DIR
                      or '.projects'. Use a temp directory for isolated tests.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle with proper resource cleanup."""
        resolved_db_path = db_path if db_path is not None else os.environ.get("INKFOUNDRY_DB_PATH", "state.db")
        resolved_projects_dir = (
            projects_dir
            if projects_dir is not None
            else os.environ.get("INKFOUNDRY_PROJECTS_DIR", ".projects")
        )
        db = StateDB(resolved_db_path)
        app.state.db = db
        app.state.default_db_path = resolved_db_path
        app.state.project_manager = ProjectManager(resolved_projects_dir)
        app.state.pipeline_manager = PipelineManager()
        if seed_data:
            _seed_sample_data(db)
        _init_token_tracker(db)
        yield
        db.close()

    app = FastAPI(title="InkFoundry Studio", lifespan=lifespan)

    # --- Status & Health ---
    @app.get("/status")
    def get_status(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> ProjectStatus:
        """Get the current project status."""
        return ProjectStatus(**_safe_project_status(db, pipeline_status=pipeline_manager.get_status(db)))

    @app.get("/health")
    def health_check() -> Dict[str, bool]:
        """Health check endpoint."""
        return {"healthy": True}

    # --- Configuration Center ---
    @app.get("/api/config")
    def get_config(db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Get current configuration from database."""
        config = _get_effective_config(db)
        if config["llm_api_key"]:
            config["llm_api_key_masked"] = (
                "****" + config["llm_api_key"][-4:]
                if len(config["llm_api_key"]) > 4
                else "****"
            )
            config["llm_api_key"] = ""
        return config

    @app.post("/api/config")
    def save_config(body: ConfigSave, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Save configuration to database."""
        import json

        existing_config = _load_stored_config(db)
        new_config = existing_config.copy()
        for field_name in body.model_fields_set:
            value = getattr(body, field_name)
            if value is not None:
                if field_name == "llm_base_url":
                    new_config[field_name] = normalize_base_url(value)
                elif field_name == "default_model":
                    new_config[field_name] = normalize_model_name(value)
                elif field_name.endswith("_model"):
                    new_config[field_name] = value.strip()
                else:
                    new_config[field_name] = value

        effective_config = _get_effective_config(db)
        effective_config.update(new_config)

        try:
            _validate_effective_config(effective_config)
        except InvalidLLMConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        db.conn.execute(
            "INSERT OR REPLACE INTO state (key, data, version) VALUES (?, ?, 1)",
            ("config", json.dumps(new_config)),
        )
        db.conn.commit()

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
        return _current_state_snapshot_response(db)

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

        config = _get_engine_config_or_http(db)
        project_brief = _get_project_brief(db)
        genre = (body.genre or project_brief.get("genre") or "xuanhuan").strip() or "xuanhuan"
        title = (body.title or project_brief.get("title") or "Untitled").strip() or "Untitled"
        summary = (body.summary if body.summary is not None else project_brief.get("summary") or "").strip()
        total_chapters = _normalize_target_chapters(
            body.total_chapters if body.total_chapters is not None else project_brief.get("target_chapters"),
            default=100,
        )

        if not summary:
            raise HTTPException(status_code=422, detail="Project summary is required before generating an outline")

        agent = OutlineAgent()
        if config and config.llm.api_key:
            agent = OutlineAgent(
                model_name=config.role_models.get("navigator", config.llm.default_model),
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
            )
            outline = await agent.arun(
                genre=genre,
                title=title,
                summary=summary,
                total_chapters=total_chapters,
            )
        else:
            outline = agent.run(
                genre=genre,
                title=title,
                summary=summary,
                total_chapters=total_chapters,
            )
        db.save_outline(outline)
        return {
            "message": "Outline generated",
            "outline": outline.model_dump(),
            "mode": "model" if config and config.llm.api_key else "fallback",
        }

    @app.put("/api/outlines")
    def update_outline(body: OutlineGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        from Engine.agents.outline import OutlineAgent

        project_brief = _get_project_brief(db)
        genre = (body.genre or project_brief.get("genre") or "xuanhuan").strip() or "xuanhuan"
        title = (body.title or project_brief.get("title") or "Untitled").strip() or "Untitled"
        summary = (body.summary if body.summary is not None else project_brief.get("summary") or "").strip()
        total_chapters = _normalize_target_chapters(
            body.total_chapters if body.total_chapters is not None else project_brief.get("target_chapters"),
            default=100,
        )
        if not summary:
            raise HTTPException(status_code=422, detail="Project summary is required before generating an outline")

        agent = OutlineAgent()
        outline = agent.run(
            genre=genre,
            title=title,
            summary=summary,
            total_chapters=total_chapters,
        )
        db.save_outline(outline)
        return {"message": "Outline updated", "outline": outline.model_dump(), "mode": "fallback"}

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
    async def run_chapter(
        chapter_num: int,
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, Any]:
        """Run a single chapter and wait for completion."""
        _require_real_chapter_model(db)
        return await pipeline_manager.run_chapter_sync(chapter_num, db)

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
    def reject_chapter(chapter_num: int, body: ReviewRejectRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Reject a chapter — set status to 'draft' with review note."""
        ch = db.get_chapter(chapter_num)
        if ch is None:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_num} not found")
        ch.status = "draft"
        if body.note:
            ch.review_notes = f"{ch.review_notes or ''}\n审核拒绝: {body.note}"
        ch.updated_at = datetime.now().isoformat()
        db.update_chapter(ch)
        return {"message": f"Chapter {chapter_num} rejected"}

    @app.post("/api/pipeline/run-batch")
    async def run_batch(
        body: PipelineStart,
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, Any]:
        """Run batch and wait for completion."""
        return await pipeline_manager.run_batch_sync(body.start_chapter, body.end_chapter, db)

    @app.get("/api/pipeline/status")
    def pipeline_status(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, Any]:
        """Get current pipeline status for the resolved project context."""
        return pipeline_manager.get_status(db)

    @app.post("/api/pipeline/pause")
    def pipeline_pause(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, str]:
        """Pause the pipeline."""
        return pipeline_manager.pause(db)

    @app.post("/api/pipeline/resume")
    def pipeline_resume(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, str]:
        """Resume the pipeline."""
        return pipeline_manager.resume(db)

    @app.post("/api/pipeline/stop")
    def pipeline_stop(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, str]:
        """Stop the pipeline."""
        return pipeline_manager.stop(db)

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
    @app.get("/api/projects")
    def list_projects(project_manager: ProjectManager = Depends(_get_project_manager)) -> Dict[str, Any]:
        """List all active projects with chapter stats."""
        projects = project_manager.list_projects(status="active")
        return {"projects": [_build_project_payload(project) for project in projects]}

    @app.post("/api/projects")
    def create_project(
        body: ProjectCreate,
        project_manager: ProjectManager = Depends(_get_project_manager),
    ) -> Dict[str, Any]:
        """Create a new project."""
        title = body.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Project title is required")
        summary = body.summary.strip()
        if not summary:
            raise HTTPException(status_code=422, detail="Project summary is required")
        target_chapters = _normalize_target_chapters(body.target_chapters, default=100)
        info = project_manager.create_project(
            title=title,
            genre=body.genre,
            summary=summary,
            target_chapters=target_chapters,
        )
        return {"message": f"Project '{title}' created", "project": _build_project_payload(info)}

    @app.get("/api/projects/active")
    def get_active_project(
        request: Request,
        response: Response,
        project_manager: ProjectManager = Depends(_get_project_manager),
    ) -> Dict[str, Any]:
        """Get the currently active project for this client session, if any."""
        project_id = _resolve_active_project_id(request)
        if not project_id:
            return {"project": None}

        info = _get_active_catalog_project(project_manager, project_id)
        if info is None:
            _clear_active_project_cookie(request, response)
            return {"project": None}

        return {"project": _build_project_payload(info)}

    @app.get("/api/projects/{project_id}")
    def get_project(
        project_id: str,
        project_manager: ProjectManager = Depends(_get_project_manager),
    ) -> Dict[str, Any]:
        """Get project details."""
        info = project_manager.get_project(project_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return {"project": _build_project_payload(info)}

    @app.delete("/api/projects/{project_id}")
    def delete_project(
        project_id: str,
        request: Request,
        response: Response,
        project_manager: ProjectManager = Depends(_get_project_manager),
    ) -> Dict[str, str]:
        """Soft-delete a project."""
        success = project_manager.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        if _resolve_active_project_id(request) == project_id:
            _clear_active_project_cookie(request, response)

        return {"message": f"Project '{project_id}' deleted"}

    @app.post("/api/projects/{project_id}/activate")
    def activate_project(
        project_id: str,
        request: Request,
        response: Response,
        project_manager: ProjectManager = Depends(_get_project_manager),
    ) -> Dict[str, str]:
        """Select a project for this client session."""
        info = _get_active_catalog_project(project_manager, project_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        _set_active_project_cookie(request, response, project_id)

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
        snapshot = _build_current_snapshot(db)
        version = db.save_snapshot(snapshot)
        return {"message": f"Snapshot v{version} saved", "version": version}

    @app.post("/api/snapshots/{version}/restore")
    def restore_snapshot(version: int, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Restore state from a snapshot."""
        snapshot = db.load_snapshot(version)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"Snapshot v{version} not found")

        _restore_snapshot_state(db, snapshot)
        return {"message": f"Restored to snapshot v{version}"}

    @app.delete("/api/snapshots/{version}")
    def delete_snapshot(version: int, db: StateDB = Depends(_get_db)) -> Dict[str, str]:
        """Delete a snapshot."""
        if not db.delete_snapshot(version):
            raise HTTPException(status_code=404, detail=f"Snapshot v{version} not found")
        return {"message": f"Snapshot v{version} deleted"}

    @app.get("/api/status")
    def api_status(
        db: StateDB = Depends(_get_db),
        pipeline_manager: PipelineManager = Depends(_get_pipeline_manager),
    ) -> Dict[str, Any]:
        """Get project status from database."""
        return _safe_project_status(db, pipeline_status=pipeline_manager.get_status(db))

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
        return _current_state_snapshot_response(db)

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
    async def generate_side_story(body: SideStoryGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Generate a side story (番外) based on characters and setting."""
        from Engine.agents.side_story import SideStoryAgent
        config = _get_engine_config_or_http(db)

        # Use mock if no valid API key or LLM not reachable
        if not config or not config.llm.api_key or not config.llm.base_url:
            agent = SideStoryAgent(model_name="dummy")
            content = agent.run({
                "characters": body.characters,
                "setting": body.setting,
                "topic": body.topic,
            })
            return {"content": content}

        try:
            agent = SideStoryAgent(
                model_name=config.role_models.get("writer", config.llm.default_model),
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
            )
            content = await agent.arun({"characters": body.characters, "setting": body.setting, "topic": body.topic})
            return {"content": content}
        except Exception:
            # Fallback to mock on LLM failure
            agent = SideStoryAgent(model_name="dummy")
            content = agent.run({
                "characters": body.characters,
                "setting": body.setting,
                "topic": body.topic,
            })
            return {"content": content}

    # --- Imitation API ---
    @app.post("/api/imitation/generate")
    async def generate_imitation(body: ImitationGenerate, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Generate content imitating the style of a sample text."""
        from Engine.agents.imitation import ImitationAgent
        config = _get_engine_config_or_http(db)

        # Use mock if no valid API key or LLM not reachable
        if not config or not config.llm.api_key or not config.llm.base_url:
            agent = ImitationAgent(model_name="dummy")
            content = agent.run({
                "sample_text": body.sample_text,
                "topic": body.topic,
            })
            return {"content": content}

        try:
            agent = ImitationAgent(
                model_name=config.role_models.get("writer", config.llm.default_model),
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
            )
            content = await agent.arun({"sample_text": body.sample_text, "topic": body.topic})
            return {"content": content}
        except Exception:
            # Fallback to mock on LLM failure
            agent = ImitationAgent(model_name="dummy")
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

    # --- AI Detection ---
    @app.post("/api/ai-detect")
    async def ai_detect(body: AIDetectRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Analyze text for AI-generated patterns."""
        from Engine.llm.ai_filter import AIFilter
        from Engine.llm.gateway import LLMGateway

        if not body.text.strip():
            raise HTTPException(status_code=400, detail="Text is empty")

        # Run rule-based analysis
        ai_filter = AIFilter(voice_profile={})
        issues = ai_filter.analyze(body.text)
        score = ai_filter.score(body.text)

        # Try LLM deep analysis if API key available
        llm_feedback = ""
        suggestions: List[str] = []
        config = _get_engine_config_or_http(db)
        if config and config.llm.api_key and config.llm.base_url:
            try:
                prompt = (
                    "分析以下文本的AI写作痕迹，返回JSON格式：\n"
                    '{"human_score": 0-100, "issues": ["问题描述"], "suggestions": ["修改建议"]}\n\n'
                    f"文本：{body.text[:3000]}"
                )
                gateway = LLMGateway(
                    model=config.role_models.get("writer", config.llm.default_model),
                    api_key=config.llm.api_key,
                    base_url=config.llm.base_url,
                )
                response = await gateway.chat(messages=[{"role": "user", "content": prompt}])
                import json as _json
                result = _json.loads(response)
                llm_feedback = f"LLM 评分: {result.get('human_score', 'N/A')}/100"
                suggestions = result.get("suggestions", [])
            except Exception:
                llm_feedback = "LLM 分析不可用"

        return {
            "score": score,
            "issue_count": len(issues),
            "issues": [
                {"type": i.type, "severity": i.severity, "description": i.description}
                for i in issues
            ],
            "llm_feedback": llm_feedback,
            "suggestions": suggestions,
        }

    # --- Trend Analysis ---
    @app.post("/api/trends/analyze")
    async def analyze_trends(body: TrendAnalyzeRequest, db: StateDB = Depends(_get_db)) -> Dict[str, Any]:
        """Analyze web novel trends using LLM."""
        from Engine.llm.gateway import LLMGateway

        config = _get_engine_config_or_http(db)

        if not config or not config.llm.api_key or not config.llm.base_url:
            # Fallback: return mock data
            return {
                "topics": [
                    {"name": "系统流", "heat": 85, "trend": "up"},
                    {"name": "克苏鲁", "heat": 72, "trend": "up"},
                    {"name": "凡人流", "heat": 68, "trend": "stable"},
                    {"name": "无限流", "heat": 55, "trend": "down"},
                ],
                "market_insights": [
                    "系统流持续热门，读者偏好轻松日常向",
                    "克苏鲁题材融合东方元素是新兴趋势",
                    "长篇作品前3章决定留存率，节奏要快",
                ],
                "recommendations": [
                    "开篇直接进入核心冲突，避免大段世界观铺垫",
                    "每章末尾设置钩子，提高追读率",
                    "加入轻松元素平衡严肃基调",
                ],
                "genre_trends": {
                    "genre": body.genre or "综合",
                    "top_tags": ["系统", "轻松", "升级", "日常"],
                    "emerging_tags": ["克苏鲁", "群像", "幕后流"],
                    "declining_tags": ["后宫", "无脑爽"],
                },
            }

        try:
            genre_context = f"题材: {body.genre}" if body.genre else ""
            keyword_context = f"关键词: {', '.join(body.keywords)}" if body.keywords else ""
            prompt = (
                f"基于当前网文市场趋势，生成一份趋势分析报告。{genre_context} {keyword_context}\n\n"
                "返回JSON格式：\n"
                "{\n"
                '  "topics": [{"name": "话题名", "heat": 0-100, "trend": "up|stable|down"}],\n'
                '  "market_insights": ["市场洞察1", ...],\n'
                '  "recommendations": ["创作建议1", ...],\n'
                '  "genre_trends": {"genre": "题材", "top_tags": [], "emerging_tags": [], "declining_tags": []}\n'
                "}\n"
            )
            gateway = LLMGateway(
                model=config.role_models.get("navigator", config.llm.default_model),
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
            )
            response = await gateway.chat(messages=[{"role": "user", "content": prompt}])
            import json as _json
            return _json.loads(response)
        except Exception:
            # Fallback on LLM failure
            return {
                "topics": [
                    {"name": "系统流", "heat": 85, "trend": "up"},
                    {"name": "克苏鲁", "heat": 72, "trend": "up"},
                    {"name": "凡人流", "heat": 68, "trend": "stable"},
                ],
                "market_insights": ["LLM 分析失败，显示默认数据"],
                "recommendations": ["开篇直接进入核心冲突"],
                "genre_trends": {"genre": body.genre or "综合", "top_tags": [], "emerging_tags": [], "declining_tags": []},
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
