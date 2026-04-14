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
| **Controller** | Pipeline with retry, circuit breaker, graceful degradation, watchdog timeout |
| **EventBus** | In-process event pub/sub for cross-component communication |
| **ReviewPolicyManager** | Configurable approval policies (strict, milestone, headless) |
| **GradientRewriter** | Escalating rewrite protocol (patch → re-context → pivot) |
| **MemoryBank** | ChromaDB-backed vector memory with fallback mode |
| **NovelImporter/Exporter** | TXT, Markdown, EPUB import/export with path traversal protection |
| **TokenTracker** | Per-session token usage accounting |
| **ProjectManager** | Project lifecycle and metadata management |
| **DaemonScheduler** | Background task queue for automatic novel generation |
| **GenreValidator** | Genre-specific constraint validation |
| **WriterAgent** | Draft generation from task cards |
| **EditorAgent** | Logic and style review |
| **RedTeamAgent** | Adversarial plot attack |
| **NavigatorAgent** | Pacing control via tension heatmap |
| **DirectorAgent** | Sandbox control, loop detection |
| **VoiceSandbox** | Character voice profile injection into prompts |
| **SideStoryAgent** | Side story / spin-off generation |
| **ImitationAgent** | Style imitation learning |
| **LLMGateway** | Unified LLM API client with retry, streaming, timeout |
| **PromptBuilder** | Composable prompt assembly with constraint injection |
| **AIFilter** | AI-powered content safety filter |
| **StyleExtractor** | Prose style extraction and analysis |
| **ModelRouter** | Hierarchical LLM routing (default → role-specific → task override) |
| **EngineConfig** | Environment variable loader for API keys, endpoints, per-role models |
| **MCPServer** | Standard protocol exposing StateDB operations |

### Layer 2: Studio (Command Surface)

| Component | Purpose |
|-----------|---------|
| **Studio API** | FastAPI REST + WebSocket backend with lifespan-managed StateDB |
| **MCP Server** | Standard protocol exposing StateDB operations |
| **Dashboard** | React SPA (Vite + shadcn/ui), workspace view with real-time pipeline push |

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
198 tests passing, 94% coverage
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
│   ├── core/                  # StateDB, Filter, Controller, EventBus, Memory, MCP, Daemon, etc.
│   ├── agents/                # Writer, Editor, RedTeam, Navigator, Director, Voice, SideStory, Imitation
│   ├── llm/                   # LLMGateway, PromptBuilder, AIFilter, StyleExtractor
│   ├── utils/                 # ModelRouter
│   ├── configs/voices/        # Voice profile templates
│   └── __init__.py
├── Studio/
│   └── api.py                 # FastAPI REST + WebSocket with lifespan-managed StateDB
├── tests/                     # 198 tests mirroring Engine structure
├── docs/                      # Plans, architecture, development guide
├── frontend/                  # React SPA (Vite + shadcn/ui) — planned
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
