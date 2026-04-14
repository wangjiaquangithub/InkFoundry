# InkFoundry Development Guide

<!-- AUTO-GENERATED: Updated from requirements.txt, .env.example, and source -->

## Prerequisites

- Python 3.10+ (tested on 3.14)
- Git

## Setup

```bash
# Clone repository
git clone <repo-url>
cd InkFoundry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-cov` | Test coverage reporting |
| `pydantic` | Data models (CharacterState, WorldState, StateSnapshot) |
| `pyyaml` | Voice profile configuration loading |
| `mcp` | Model Context Protocol server for StateDB |
| `fastapi` | Studio REST API backend |
| `uvicorn` | ASGI server for FastAPI |
| `httpx` | HTTP client for testing FastAPI |

## Available Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run full test suite |
| `pytest tests/core/test_state_db.py -v` | Run specific test file |
| `pytest tests/core/test_state_db.py::test_update_and_retrieve_character -v` | Run single test |
| `pytest --cov=Engine --cov-report=term-missing` | Run tests with coverage report |
| `pytest tests/test_integration.py -v` | Run integration tests only |
| `uvicorn Studio.api:app --reload` | Start Studio API with hot reload |

## Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=Engine --cov-report=term-missing

# By module
pytest tests/core/ -v        # Core infrastructure tests
pytest tests/agents/ -v      # Agent tests
pytest tests/utils/ -v       # Utility tests
pytest tests/studio/ -v      # Studio API tests
pytest tests/test_integration.py -v  # Integration tests
```

### Writing New Tests

All tests follow TDD convention:
- Test files live in `tests/` mirroring `Engine/` structure
- Fixtures defined in `tests/conftest.py` (e.g., `db_instance`)
- Use `monkeypatch.setenv()` for environment variable tests
- Test class methods by instantiating directly, no mocks unless unavoidable

### Coverage Target

Minimum **80%** line coverage. Current: **95%** (73 tests).

## Code Style

- **Immutability**: Create new objects, never mutate existing ones
- **File organization**: One responsibility per file, 200-400 lines typical
- **Error handling**: Handle errors explicitly at every level
- **Input validation**: Validate at system boundaries, fail fast
- **Type annotations**: Use `from __future__ import annotations` for forward refs

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- One logical change per commit
- TDD workflow: RED → GREEN → REFACTOR → commit
- No hardcoded secrets — use environment variables

## Architecture Overview

See [`Architecture_V3.md`](../Architecture_V3.md) for the full system design.

### Quick Reference

| Component | File | Purpose |
|-----------|------|---------|
| StateDB | `Engine/core/state_db.py` | SQLite single source of truth |
| StateFilter | `Engine/core/filter.py` | State-Over-Vector hard truth filter |
| Controller | `Engine/core/controller.py` | Pipeline with retry/circuit breaker |
| Models | `Engine/core/models.py` | Pydantic state models |
| BaseAgent | `Engine/agents/base.py` | Abstract agent interface |
| ModelRouter | `Engine/utils/router.py` | Hierarchical LLM routing |
| EngineConfig | `Engine/config.py` | Environment variable loader |
