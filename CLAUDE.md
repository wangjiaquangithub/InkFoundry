# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**InkFoundry** is a "Narrative OS" — a dual-layer system for AI-assisted long-form novel generation. It combines an **Industrial Automation Engine** (Python) with a **Visual Insight Studio** (planned UI layer).

**Core problems it solves**: "logic collapse", "AI flavor", "context amnesia", and "system deadlock" in mass-producing long-form novels.

**Architecture**: See `Architecture_V3.md` for the full v3.2 blueprint.

## Tech Stack

- **Language**: Python 3.10+
- **Database**: SQLite (StateDB with atomic locks/snapshots)
- **Testing**: pytest
- **Planned**: FastAPI (Studio backend), ChromaDB (vector memory), MCP (tool protocol), Pydantic (models)

## Project Structure

```
InkFoundry/
├── Engine/                  # Layer 1: Execution Engine
│   ├── core/                # StateDB, MemoryBank, Controller
│   ├── agents/              # Writer, Editor, RedTeam, Navigator, Director
│   ├── templates/           # Genre templates (config & prompts)
│   └── utils/               # Anti-AI filters, formatting checks
├── Studio/                  # Layer 2: Command Surface / UI (planned)
├── tests/                   # Test suite
├── docs/                    # Build plans and documentation
└── Architecture_V3.md       # System architecture reference
```

## Key Architecture Concepts

### StateDB (Single Source of Truth)
- SQLite-backed key-value store with atomic locking and version-based optimistic concurrency
- Supports lock/release for concurrent agent safety
- See `Engine/core/state_db.py` (planned at `Engine/core/state_db.py`)

### State-Over-Vector Filter
- RAG results from MemoryBank pass through StateFilter before context injection
- If StateDB contradicts RAG recall, StateDB wins (hard truth filter)
- See `tests/core/test_state_db.py` for filter test cases

### Gradient Rewrite Protocol
- Retry 1: Localized patch (single paragraph)
- Retry 2: Re-context with State_Snapshot
- Retry 3: Pivot strategy (plot change proposal)

### Pipeline Controller
- Manages task lifecycle with watchdog timeout and circuit breaker (max_retries=3)
- Graceful degradation on retry 3

### Review Policies
- **Strict**: User approves every chapter
- **Milestone**: AI runs autonomously, interrupts on logic branches
- **Headless**: Fire-and-forget

## Development Commands

### Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/core/test_state_db.py -v

# Run with coverage
pytest --cov=Engine --cov-report=term-missing
```

### Python Environment
```bash
# Create virtual environment (if not exists)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # When created
```

## Current State

The project is in **Phase 0 (MVP)** — core engine infrastructure. Tests exist in `tests/core/test_state_db.py` but the corresponding implementation files are not yet created. The architecture is fully specified in `Architecture_V3.md` and `docs/build_plan.md`.

### What Exists
- Architecture documentation (v3.2)
- Detailed build plan (`docs/build_plan.md`)
- Test suite for StateDB (`tests/core/test_state_db.py`)
- Package scaffolding (`Engine/__init__.py`, `Engine/core/__init__.py`, `Engine/agents/__init__.py`)

### What Needs Building (per build_plan.md)
1. `Engine/core/models.py` — Pydantic models (CharacterState, WorldState, StateSnapshot)
2. `Engine/core/state_db.py` — SQLite StateDB with atomic locks
3. `Engine/core/filter.py` — State-Over-Vector Filter
4. `Engine/core/controller.py` — Pipeline Controller with watchdog/circuit breaker
5. `Engine/agents/base.py` — Base agent interface
6. `Engine/agents/writer.py` — Writer agent
7. `Engine/agents/editor.py` — Editor agent
8. `Engine/agents/redteam.py` — RedTeam agent
9. `Engine/agents/navigator.py` — Navigator agent with tension heatmap
10. `Engine/agents/director.py` — Director agent for sandbox control
11. `Engine/core/memory_bank.py` — Vector memory (ChromaDB)
12. `Engine/core/mcp_server.py` — MCP server exposing StateDB
13. `Engine/utils/router.py` — Hierarchical model router
14. `Engine/core/review_policy.py` — Review policy manager
15. `Studio/api.py` — FastAPI Studio backend

## Rules

- **TDD is mandatory**: Write tests first (RED), implement (GREEN), refactor (IMPROVE) — see `rules/common/testing.md`
- **80% minimum test coverage** required
- **Code review** required after writing code — use `code-reviewer` agent
- **No hardcoded secrets** — use environment variables
- Follow immutability patterns (create new objects, don't mutate existing ones)
