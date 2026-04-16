# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

InkFoundry is a long-form novel generation system with three practical layers:

- **Engine** (`Engine/`) — domain logic, persistence, orchestration, agents, LLM wrappers, import/export.
- **Studio API** (`Studio/api.py`) — the FastAPI backend, WebSocket endpoint, and effective BFF for the frontend.
- **Frontend** (`frontend/`) — a React + Vite SPA that mostly wraps backend endpoints into page-level tools.

`README.md` and `Architecture_V3.md` describe the intended blueprint. When they conflict with the code, trust the **current implementation**.

## Common commands

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Backend

```bash
uvicorn Studio.api:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

Vite proxies `/api`, `/health`, `/status`, and `/ws` to `localhost:8000` via `frontend/vite.config.ts`.

### Tests

Use `python3 -m pytest` instead of assuming `pytest` is on PATH.

```bash
python3 -m pytest
python3 -m pytest tests/studio/test_api.py -q
python3 -m pytest tests/studio/test_api.py::test_generate_outline -q
python3 -m pytest tests/core/test_state_db.py -q
python3 -m pytest --cov=Engine --cov-report=term-missing
```

## Architecture that matters in practice

### `StateDB` is the center of the system

Start here for most backend work:

- `Engine/core/models.py`
- `Engine/core/state_db.py`
- `Studio/api.py`

`StateDB` is not just a small state store; it owns most persisted novel data: chapters, outlines, characters, profiles, relationships, world-building data, snapshots, and config-adjacent state.

### Chapter generation is orchestrated in one place

`Engine/core/orchestrator.py` is the main execution path.

Current flow:

- Navigator creates a task card
- MemoryBank recall is optionally filtered through `StateFilter`
- Writer generates a draft
- Editor reviews it
- RedTeam attacks it
- Review policy determines status
- Chapter is saved back to `StateDB`
- Events are published to the in-process `EventBus`

If a change affects chapter generation behavior, inspect `orchestrator.py` before changing individual agents.

### `Studio/api.py` is the real backend entrypoint

Most backend behavior is centralized there: lifecycle, config, projects, chapters, outlines, pipeline control, snapshots, token stats, import/export, trend/style/AI-detect endpoints, WebSocket, and SPA serving.

When looking for a route, search `Studio/api.py` first.

### Multi-project support is one SQLite DB per project

`Engine/core/project_manager.py` manages project metadata in `.projects/catalog.db` and creates one SQLite file per project under `.projects/<project_id>.db`.

Important detail: activating a project via `/api/projects/{project_id}/activate` swaps `app.state.db` to that project's `StateDB`. Project context is therefore **process-global on the backend**, not request-scoped.

### Frontend project state is separate from backend active project state

The frontend stores the selected book in React context (`currentBook` in `frontend/src/App.tsx`), while the backend tracks the active project by replacing `app.state.db`.

This split matters:

- refreshing the SPA can lose `currentBook` even if the backend still has an active project
- project-scoped bugs often involve `frontend/src/App.tsx`, `frontend/src/pages/Projects.tsx`, and `Studio/api.py` together

### The frontend is page-driven and API-thin

Useful files:

- `frontend/src/App.tsx` — route layout, system menu vs book-scoped menu, `BookGuard`
- `frontend/src/api/client.ts` — the frontend API surface
- `frontend/src/pages/*` — page-level feature wrappers

Most pages do not model project resources by URL; they operate on whichever backend project is currently active.

## Important implementation notes

### Prefer `/api/*` endpoints for new work

The backend still exposes some older non-`/api` endpoints such as `/characters` and `/state/snapshot` alongside `/api/*` equivalents. Prefer the `/api/*` surface unless maintaining legacy behavior or tests.

### Pipeline control uses a singleton manager

`Studio/api.py` uses a global `PipelineManager` for run/pause/resume/stop behavior. Pipeline state is shared at the app level, similar to project activation.

### Advanced features may return degraded or placeholder results

Several LLM-facing features fall back to mock, dummy, or heuristic behavior when config is missing or a call fails. This is especially relevant for:

- side story generation
- imitation generation
- trend analysis
- parts of the chapter pipeline when real LLM config is unavailable

Do not assume every successful API response came from a real model-backed path.

### Config is read from both env and DB-backed state

`.env.example` defines environment variables, but `Studio/api.py` also reads and writes config via `/api/config` and stores it in the database. If config behavior looks inconsistent, inspect both env vars and the `state` table-backed config path.

### API tests use the app factory with an in-memory DB

`tests/studio/test_api.py` uses:

```python
create_app(seed_data=False, db_path=":memory:")
```

Use that pattern for isolated API tests.

### There is no checked-in Python lint/format config

The repo has frontend linting, but no repository-level Python tooling config like `pyproject.toml` for Ruff/Black/Mypy. Do not assume Python lint/format commands are wired into the project.

## Read these first for non-trivial tasks

- `Studio/api.py`
- `Engine/core/state_db.py`
- `Engine/core/models.py`
- `Engine/core/orchestrator.py`
- `Engine/core/project_manager.py`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- the specific page under `frontend/src/pages/` that owns the feature you are touching
