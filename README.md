# InkFoundry

> **Narrative OS** — A dual-layer system for AI-assisted long-form novel generation.

## The Problem

Mass-producing long-form novels with LLMs suffers from four fundamental failures:

| Problem | Symptom |
|---------|---------|
| **Logic Collapse** | Characters act inconsistently, plot holes emerge |
| **AI Flavor** | All characters sound the same, homogenized prose |
| **Context Amnesia** | RAG recalls contradict established story facts |
| **System Deadlock** | Endless retry loops with no escape hatch |

## The Solution

InkFoundry solves these through **industrial automation principles** applied to narrative generation:

```
Navigator ──> Writer ──> Editor ──> RedTeam
    ^                                 |
    |          ┌─ StateDB ──┐         |
    └──────────│ StateOver  │<────────┘
               │ Vector     │
               │ Filter     │
               └────────────┘
```

**StateDB** is the single source of truth. A character's state in StateDB always wins over RAG recall — if the database says "deceased," no amount of vector search will resurrect them.

## Architecture

### Layer 1: Engine (Execution)

| Component | Purpose |
|-----------|---------|
| **StateDB** | SQLite-backed state store with atomic locks, versioning, snapshots |
| **StateFilter** | Hard truth filter — StateDB blocks contradictory RAG results |
| **Controller** | Pipeline with retry, circuit breaker, graceful degradation |
| **WriterAgent** | Draft generation from task cards |
| **EditorAgent** | Logic and style review |
| **RedTeamAgent** | Adversarial plot attack |
| **NavigatorAgent** | Pacing control via tension heatmap |
| **DirectorAgent** | Sandbox control, loop detection |
| **ModelRouter** | Hierarchical LLM routing (default → role-specific → task override) |
| **EngineConfig** | Environment variable loader for API keys, endpoints, per-role models |

### Layer 2: Studio (Command Surface)

| Component | Purpose |
|-----------|---------|
| **Studio API** | FastAPI REST backend for character management |
| **MCP Server** | Standard protocol exposing StateDB operations |
| **Dashboard** | *(planned)* Tension heatmap, causality graph, manual intervention |

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd InkFoundry

# 2. Setup virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API key and model settings

# 5. Run tests
pytest
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DEFAULT_MODEL=qwen3.6-plus
WRITER_MODEL=qwen3.6-plus
EDITOR_MODEL=qwen3.6-plus
REDTEAM_MODEL=qwen3.6-plus
NAVIGATOR_MODEL=qwen3.6-plus
```

All variables are loaded via `EngineConfig.from_env()`. Missing `LLM_API_KEY` raises `ValueError`.

## Key Mechanisms

### State-Over-Vector Filter

RAG results pass through `StateFilter` before context injection. If RAG recalls "Character A is alive" but StateDB says "Character A died" — **the RAG result is blocked**.

### Pipeline Controller

```
Retry 1 → Retry 2 → Retry 3 → Circuit Breaker
```

On Retry 3, `graceful_degradation=True` returns a fallback instead of raising, saving progress.

### Hierarchical Model Routing

| Level | Override | Example |
|-------|----------|---------|
| L1 | Global default | `qwen-plus` for everything |
| L2 | Per-role model | Writer uses `qwen-plus`, Editor uses `claude-sonnet` |
| L3 | Task importance | Climax chapters use `claude-opus` |

## Test Results

```
73 tests passing, 95% coverage
```

Run with coverage:
```bash
pytest --cov=Engine --cov-report=term-missing
```

## Project Structure

```
InkFoundry/
├── Engine/
│   ├── config.py              # Environment config loader
│   ├── core/                  # StateDB, Filter, Controller, Models, Memory, MCP
│   ├── agents/                # Writer, Editor, RedTeam, Navigator, Director, Voice
│   ├── utils/                 # ModelRouter
│   ├── configs/voices/        # Voice profile templates
│   └── __init__.py
├── Studio/
│   └── api.py                 # FastAPI REST backend
├── tests/                     # 73 tests mirroring Engine structure
├── docs/                      # Plans, architecture, development guide
├── Architecture_V3.md         # Full system blueprint
├── .env.example               # Environment variable template
└── requirements.txt
```

## Development

- **TDD mandatory** — Write tests first (RED), implement (GREEN), refactor (IMPROVE)
- **80% minimum coverage** required
- **Conventional commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for the full development guide.

## License

MIT
