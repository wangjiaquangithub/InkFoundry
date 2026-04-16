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
| L1 | Global default | `qwen3.6-plus` for everything |
| L2 | Per-role model | Writer uses `qwen3.6-plus`, Editor uses `claude-sonnet` |
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

---

## 项目简介

**InkFoundry**（中文代号：**叙事引擎**）是一个面向 AI 辅助长篇小说创作的「叙事操作系统」。

### 核心问题

大语言模型批量生成长篇小说时存在四个根本性缺陷：

| 问题 | 症状 |
|------|------|
| **逻辑崩溃** | 角色行为前后矛盾，剧情出现漏洞 |
| **AI 腔调** | 所有角色说话一个味儿，文风同质化 |
| **上下文失忆** | RAG 检索结果与已建立的故事事实矛盾 |
| **系统死锁** | 无限重试循环，无退出机制 |

### 解决方案

InkFoundry 通过**工业自动化原理**解决这些问题：

```
导航器 ──> 写手 ──> 编辑 ──> 红队
  ^                            |
  |       ┌─ 状态数据库 ──┐     |
  └───────│ 状态 > 向量    │<────┘
          │ 过滤器        │
          └───────────────┘
```

**状态数据库（StateDB）** 是系统的唯一真相源。如果 StateDB 记录「角色已死亡」，无论 RAG 向量检索返回什么结果，都不会让这个角色复活。

### 架构分层

| 层级 | 组件 | 说明 |
|------|------|------|
| **Layer 1：引擎** | StateDB、StateFilter、Controller、WriterAgent、EditorAgent 等 27 个组件 | 核心执行引擎 |
| **Layer 2：工作室** | FastAPI REST + WebSocket、MCP Server、React Dashboard | 命令操作面 |

### 关键机制

- **状态优先过滤（State-Over-Vector）**：StateDB 的硬事实永远优先于 RAG 检索结果
- **管道控制器（Pipeline Controller）**：重试 3 次 → 熔断器 → 优雅降级，保存进度不丢失
- **分层模型路由**：全局默认 → 角色专用 → 任务覆盖三级模型选择
- **角色声音沙箱**：通过 YAML 配置文件为每个角色注入独特声音特征，避免 AI 腔

---

## 部署指南

### 环境要求

| 依赖 | 最低版本 |
|------|----------|
| Python | 3.10+ |
| 操作系统 | Linux / macOS / Windows |
| LLM API | 兼容 OpenAI 接口的任意服务（通义千问、OpenAI、本地部署等） |

### 本地开发部署

```bash
# 1. 克隆仓库
git clone <仓库地址> && cd InkFoundry

# 2. 创建虚拟环境
python -m venv .venv && source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key 和模型配置

# 5. 运行测试
pytest

# 6. 启动 Studio API
uvicorn Studio.api:app --reload
# 访问 http://localhost:8000
```

### 生产部署

```bash
# 1. 创建虚拟环境
python -m venv /opt/inkfoundry/venv
source /opt/inkfoundry/venv/bin/activate

# 2. 安装依赖
pip install --no-cache-dir -r requirements.txt

# 3. 配置环境变量（建议使用 .env.production）
cat > /opt/inkfoundry/.env << 'ENV'
LLM_API_KEY=你的正式API密钥
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DEFAULT_MODEL=qwen3.6-plus
ENV

# 4. 使用 Gunicorn + Uvicorn 启动
gunicorn Studio.api:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-logfile - \
  --error-logfile -
```

### Docker 部署（规划中）

```dockerfile
# Dockerfile 规划
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "Studio.api:app", "--bind", "0.0.0.0:8000"]
```

### 环境变量说明

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_BASE_URL` | 否 | API 端点地址，默认 `https://coding.dashscope.aliyuncs.com/v1` |
| `DEFAULT_MODEL` | 否 | 全局默认模型 |
| `WRITER_MODEL` | 否 | 写手专用模型 |
| `EDITOR_MODEL` | 否 | 编辑专用模型 |
| `REDTEAM_MODEL` | 否 | 红队专用模型 |
| `NAVIGATOR_MODEL` | 否 | 导航器专用模型 |

缺少 `LLM_API_KEY` 时，`EngineConfig.from_env()` 会抛出 `ValueError`。

## License

MIT
