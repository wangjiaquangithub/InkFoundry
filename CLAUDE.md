# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**InkFoundry** is a "Narrative OS" — a dual-layer system for AI-assisted long-form novel generation. It combines an **Execution Engine** (Python) with a **Studio** (FastAPI backend for UI dashboard).

**Core problems solved**: "logic collapse", "AI flavor", "context amnesia", and "system deadlock" in mass-producing long-form novels.

**Architecture reference**: `Architecture_V3.md` (v3.2 blueprint)

## Tech Stack

- **Python** 3.10+ (tested on 3.14)
- **SQLite** — StateDB with atomic locks, version-based optimistic concurrency, snapshot management
- **Pydantic** — data models (CharacterState, WorldState, StateSnapshot)
- **pytest** — test framework with coverage
- **FastAPI** — Studio REST API
- **MCP** (Python SDK) — protocol for exposing StateDB
- **PyYAML** — voice profile configuration
- **ChromaDB** — planned (MemoryBank currently uses in-memory placeholder)

## Project Structure

```
InkFoundry/
├── Engine/
│   ├── core/
│   │   ├── models.py          # Pydantic: CharacterState, WorldState, StateSnapshot
│   │   ├── state_db.py        # SQLite StateDB: CRUD, atomic locks, snapshots
│   │   ├── filter.py          # State-Over-Vector Filter (StateDB > RAG)
│   │   ├── controller.py      # Pipeline Controller: retry, circuit breaker
│   │   ├── memory_bank.py     # Vector memory (ChromaDB placeholder)
│   │   └── mcp_server.py      # MCP server exposing StateDB
│   ├── agents/
│   │   ├── base.py            # BaseAgent interface (run() abstract)
│   │   ├── writer.py          # Draft generation from Task Cards
│   │   ├── editor.py          # Logic & style review
│   │   ├── redteam.py         # Adversarial plot attack
│   │   ├── navigator.py       # Task Cards with tension heatmap
│   │   ├── director.py        # Role-play sandbox loop detection
│   │   └── voice_sandbox.py   # Character voice profile injection
│   ├── configs/voices/
│   │   └── default.yaml       # Default voice config
│   ├── config.py              # EngineConfig: env var loader
│   └── utils/
│       └── router.py          # Hierarchical model router
├── Studio/
│   └── api.py                 # FastAPI REST API (status, characters CRUD)
├── tests/
│   ├── conftest.py            # Shared fixtures (db_instance)
│   ├── core/                  # 6 test files: models, state_db, filter, controller, memory_bank, mcp
│   ├── agents/                # 7 test files: base, writer, editor, redteam, navigator, director, voice
│   ├── utils/                 # router tests
│   ├── studio/                # API tests
│   └── test_integration.py    # Full pipeline end-to-end tests
├── docs/
│   ├── implementation_plan.md # Task-by-task plan
│   ├── CONTRIBUTING.md        # Development guide
│   ├── plans/                 # Superpowers planning docs
│   └── superpowers/           # Superpowers skill outputs
├── .env.example               # Environment variable template
├── Architecture_V3.md         # System architecture v3.2
├── PROGRESS.log               # Build progress tracker
└── requirements.txt
```

## Key Architecture Concepts

### StateDB (Single Source of Truth)
- SQLite-backed with 4 tables: `state` (generic KV), `characters`, `world_states`, `snapshots`
- Thread-safe via `threading.Lock` with atomic lock IDs for concurrent agent safety
- Optimistic concurrency via version field (`expected_version` parameter)
- Full snapshot save/load/list for rollback support
- Lifecycle management: `close()` invalidates connection, operations after close raise `RuntimeError`

### State-Over-Vector Filter
- RAG results from MemoryBank pass through `StateFilter` before context injection
- `apply(rag_context)` — blocks entries for deceased/inactive characters in StateDB
- `check_conflict(state_db_data, rag_data)` — detects key-level conflicts between sources
- StateDB always wins over RAG recall (hard truth filter)

### Pipeline Controller
- `execute_with_retry(task_func, *args)` — retry loop with configurable `max_retries`
- `CircuitBreakerError` raised when retries exhausted
- `graceful_degradation=True` returns fallback dict instead of raising on final attempt

### Gradient Rewrite Protocol (planned)
- Retry 1: Localized patch (single paragraph)
- Retry 2: Re-context with State_Snapshot
- Retry 3: Pivot strategy (plot change proposal)

### Review Policies (planned)
- **Strict**: User approves every chapter
- **Milestone**: AI runs autonomously, interrupts on logic branches
- **Headless**: Fire-and-forget

### Hierarchical Model Router
- L1: Global default model (e.g., `qwen-plus`)
- L2: Agent-specific overrides
- L3: Task-level overrides (e.g., climax chapters use `claude-opus`)

## Development Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/core/test_state_db.py -v

# Run single test
pytest tests/core/test_state_db.py::test_update_and_retrieve_character -v

# Run with coverage
pytest --cov=Engine --cov-report=term-missing

# Run integration tests only
pytest tests/test_integration.py -v

# Start Studio API (when ready)
uvicorn Studio.api:app --reload
```

## Current State

**All 4 phases complete** — 73 tests passing, 95% coverage.

### Completed
- **Phase 0**: Core Infrastructure (StateDB, Filter, Controller, Models)
- **Phase 1**: Agent Implementation (Writer, Editor, RedTeam, Navigator, Director)
- **Phase 2**: Advanced Features (MemoryBank, Voice Sandbox, Model Router)
- **Phase 3**: Studio Integration (MCP Server, FastAPI API, Integration Tests)
- **Phase 4**: Configuration System (EngineConfig, API key wiring, `.env.example`)

### Planned/Placeholder
- ChromaDB integration (MemoryBank uses in-memory list)
- LLM API integration in agents (currently return static/mock responses)
- Watchdog timeout in Controller
- Review Policy Manager
- Studio UI frontend
- Director loop detection (simplified — only checks history length)

## Rules

- **TDD is mandatory**: Write tests first (RED), implement (GREEN), refactor (IMPROVE)
- **80% minimum test coverage** required
- **Code review** required after writing code — use `code-reviewer` agent
- Follow immutability patterns (create new objects, don't mutate existing ones)
- No hardcoded secrets — use environment variables
