# InkFoundry 完整系统设计 Spec

> **Goal**: 构建一个全面超越 InkOS 的 AI 长篇小说生成系统，解决四大痛点：AI味重、容错率低、自动化不足、效率低。
>
> **Architecture**: 双引擎架构 — Python Engine（执行层）+ React Studio（可视化控制层）
>
> **Tech Stack**: Python (FastAPI, SQLite, Pydantic) + React (Vite, shadcn/ui, Tailwind CSS, Zustand, Recharts, WebSocket)

---

## 1. 竞品对比与差异化定位

### InkOS 现状

| 维度 | InkOS 实现 | 痛点 |
|------|-----------|------|
| 状态管理 | 7 个 Truth Files（JSON） | 无原子操作、无版本并发、文件 I/O 慢 |
| 矛盾处理 | Auditor 33 维度检测 → 简单 revise → re-audit | 无硬过滤，RAG 可能引入矛盾 |
| 重试策略 | 无限 revise 循环 | Token 浪费，死循环风险 |
| 人工控制 | Human review gates（单一模式） | 不够灵活，要么全管要么不管 |
| Token 效率 | 10 个 Agent 全跑 | 每章消耗大量 Token |
| 前端 | CLI + 新推出的 Web Studio | 功能基础，体验待验证 |

### InkFoundry 差异化

| 维度 | InkFoundry 实现 | 优势 |
|------|----------------|------|
| 状态管理 | **StateDB**（SQLite 原子操作、版本并发、快照回滚） | 数据库级一致性保证 |
| 矛盾处理 | **State-Over-Vector Filter**（RAG 进 Writer 前过过滤器） | StateDB 是硬真相，矛盾直接阻断 |
| 重试策略 | **Gradient Rewrite Protocol**（Patch → Re-Context → Pivot） | 三级降级，不浪费 Token |
| 人工控制 | **Review Policy Matrix**（Strict / Milestone / Headless） | 三种模式按需切换 |
| Token 效率 | **Hierarchical Model Router**（按任务重要性选模型） | 普通章节小模型，高潮大模型 |
| 前端 | **React + shadcn/ui 小说工作台** | 三栏布局，实时可视化 |

---

## 2. 系统架构

### 2.1 项目结构

```
InkFoundry/
├── Engine/                          # Layer 1: 执行引擎
│   ├── core/
│   │   ├── models.py                # Pydantic 数据模型（含 Project）
│   │   ├── state_db.py              # SQLite StateDB（已有）
│   │   ├── filter.py                # State-Over-Vector Filter（已有）
│   │   ├── controller.py            # Pipeline Controller（已有，需增强）
│   │   ├── memory_bank.py           # Vector 记忆（需接入 ChromaDB）
│   │   ├── mcp_server.py            # MCP 协议（已有）
│   │   ├── event_bus.py             # [新增] 事件总线
│   │   ├── review_policy.py         # [新增] Review Policy Manager
│   │   ├── project_manager.py       # [新增] 多项目管理
│   │   ├── importer.py              # [新增] 导入/续写
│   │   ├── exporter.py              # [新增] 导出功能
│   │   ├── daemon.py                # [新增] 后台定时写作
│   │   ├── token_tracker.py         # [新增] Token 用量统计
│   │   └── genre_validator.py       # [新增] 题材校验器
│   ├── agents/
│   │   ├── base.py                  # BaseAgent 接口（已有）
│   │   ├── writer.py                # Writer（需接入真实 LLM）
│   │   ├── editor.py                # Editor（需接入真实 LLM）
│   │   ├── redteam.py               # RedTeam（需接入真实 LLM）
│   │   ├── navigator.py             # Navigator（已有）
│   │   ├── director.py              # Director（已有）
│   │   ├── voice_sandbox.py         # Voice Sandbox（已有）
│   │   ├── side_story.py            # [新增] 番外生成
│   │   └── imitation.py             # [新增] 仿写
│   ├── llm/                         # [新增] LLM 网关
│   │   ├── gateway.py               # LLM API 调用封装
│   │   ├── prompt_builder.py        # Prompt 模板组装
│   │   ├── ai_filter.py             # 去 AI 味检测器
│   │   └── style_extractor.py       # 风格克隆
│   ├── configs/
│   │   ├── voices/                  # Voice Profile 配置（已有）
│   │   └── genres/                  # [新增] 题材模板（xuanhuan, xianxia, urban...）
│   ├── config.py                    # EngineConfig（已有）
│   └── utils/router.py              # Model Router（已有）
│
├── Studio/                          # Layer 2: 指挥面板
│   ├── api.py                       # FastAPI REST + 静态文件 serve
│   └── ws.py                        # [新增] WebSocket handler
│
├── frontend/                        # [新增] React SPA
│   ├── src/
│   │   ├── components/ui/           # shadcn/ui 组件
│   │   ├── components/              # 业务组件
│   │   ├── pages/                   # 7 个核心页面
│   │   ├── hooks/                   # API + WebSocket hooks
│   │   ├── stores/                  # Zustand 状态管理
│   │   └── types/                   # TypeScript 类型定义
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
└── requirements.txt
```

### 2.2 数据流

```
用户操作 React SPA
    ↓ HTTP POST /api/pipeline/start
FastAPI → Engine Pipeline Controller
    ↓
Navigator 生成 Task Card → Writer 生成草稿 → Editor 审核 → RedTeam 攻击
    ↓ (每步通过 WebSocket 推送状态)
React SPA 实时更新进度
    ↓
StateDB 原子更新 → 快照保存
    ↓
输出章节内容 → 下一章
```

### 2.3 实时通信

```
WebSocket /ws/pipeline/{project_id}
    ↓ 推送事件
{
    "event": "agent_status",
    "agent": "writer",
    "status": "generating",
    "chapter": 3,
    "progress": 0.65,
    "timestamp": "2026-04-14T10:30:00Z"
}
```

---

## 3. Phase B: LLM 集成（P0）

### 3.1 LLM Gateway

**文件**: `Engine/llm/gateway.py`

- 封装 LLM API 调用（OpenAI 兼容协议）
- 支持 `api_key`、`base_url`、`model` 参数
- 内置重试（指数退避）、超时控制
- 流式输出（streaming）支持

**核心接口**:
```python
class LLMGateway:
    def __init__(self, model: str, api_key: str, base_url: str):
        ...

    async def chat(self, messages: list[dict], temperature: float = 0.7,
                   max_tokens: int = 4096, stream: bool = False) -> str | AsyncIterator[str]:
        ...

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        ...
```

### 3.2 Prompt Builder

**文件**: `Engine/llm/prompt_builder.py`

- 模板化 Prompt 组装：system prompt + context + task + constraints
- 支持注入：Voice Profile、StateDB 快照、Task Card、历史上下文
- 去 AI 味约束模板（负面提示词列表）

**核心接口**:
```python
class PromptBuilder:
    def __init__(self, system_template: str):
        ...

    def with_context(self, context: str) -> Self:
        ...

    def with_voice(self, voice_profile: dict) -> Self:
        ...

    def with_state_snapshot(self, snapshot: dict) -> Self:
        ...

    def with_constraints(self, constraints: list[str]) -> Self:
        ...

    def build(self) -> list[dict]:
        ...
```

### 3.3 AI Filter（去 AI 味检测器）

**文件**: `Engine/llm/ai_filter.py`

- Editor Agent 的专项检查模块
- 检测项：
  - 重复句式模式（连续 N 句相同结构）
  - AI 套话（"值得注意的是"、"不禁"、"仿佛"、"似乎"、"无疑"等高频词）
  - 感官密度不足（五感描写 < N 处/千字）
  - 过度修饰（形容词密度过高）
  - 情感扁平化（缺乏内心独白/动作细节）
  - 对话同质化（所有角色说话风格一致）

**核心接口**:
```python
class AIFilter:
    def __init__(self, voice_profile: dict):
        ...

    def analyze(self, text: str) -> list[AIFilterIssue]:
        """返回检测到的问题列表"""
        ...

    def score(self, text: str) -> float:
        """返回 0-100 的去 AI 味评分"""
        ...

@dataclass
class AIFilterIssue:
    type: str  # "repetitive_structure" | "ai_cliche" | "low_sensory" | ...
    severity: float  # 0-1
    description: str
    position: tuple[int, int]  # (start, end) character indices
```

### 3.4 Agent 接入真实 LLM

**修改文件**: `Engine/agents/writer.py`, `Engine/agents/editor.py`, `Engine/agents/redteam.py`

- 每个 Agent 的 `run()` 方法改为调用 `LLMGateway`
- 通过 `ModelRouter.get_model(agent_type)` 获取正确的 model/api_key/base_url
- 使用 `PromptBuilder` 组装完整 Prompt
- 支持流式输出（用于 WebSocket 实时推送）

**Writer Agent 数据流**:
```
Task Card + Voice Profile + State Snapshot + Memory Context
    ↓ PromptBuilder
Prompt (system + context + task + constraints)
    ↓ LLMGateway
生成章节草稿
    ↓ AIFilter (可选，Writer 自检)
去 AI 味评分 + 问题列表
    ↓ 返回
```

### 3.5 Voice Profile 增强

**现有文件**: `Engine/agents/voice_sandbox.py`, `Engine/configs/voices/default.yaml`

- Voice Profile 增加字段：
  - `speech_patterns`: 角色说话习惯（口头禅、句式偏好）
  - `vocabulary`: 专属词汇（专业术语、方言词）
  - `sensory_bias`: 感官偏好（视觉型角色 vs 听觉型角色）
  - `forbidden_words`: 禁用词列表（防止角色说出 OOC 的话）
- Prompt 注入时根据当前 POV 角色自动加载对应 Voice Profile

---

## 4. Phase C: Pipeline 串联（P0）

### 4.1 Pipeline Controller 增强

**修改文件**: `Engine/core/controller.py`

现有 Controller 已有 retry/circuit breaker/graceful degradation。新增：

- **看门狗超时**: 每个 Agent 任务设置硬超时（可配置，默认 10 分钟），超时后杀掉任务
- **事件总线集成**: Agent 状态变更发布到 EventBus
- **Review Policy 集成**: 根据当前策略决定是否中断用户

**新增接口**:
```python
@dataclass
class PipelineConfig:
    max_retries: int = 3
    watchdog_timeout: float = 600.0  # 10 minutes
    review_policy: str = "milestone"  # strict | milestone | headless
    graceful_degradation: bool = True

class PipelineController:
    def run_chapter(self, chapter_num: int, task_card: dict) -> dict:
        """执行单章完整 Pipeline"""
        ...

    def run_batch(self, start: int, end: int) -> dict:
        """批量执行章节"""
        ...
```

### 4.2 Event Bus（事件总线）

**文件**: `Engine/core/event_bus.py`

- 轻量级进程内事件总线（pub/sub 模式）
- Agent 状态变更自动发布事件
- WebSocket handler 订阅事件并推送前端

**核心接口**:
```python
class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[callable]] = {}

    def subscribe(self, event_type: str, callback: callable):
        ...

    def publish(self, event_type: str, data: dict):
        ...

# 事件类型
EVENT_AGENT_STATUS = "agent_status"
EVENT_CHAPTER_COMPLETE = "chapter_complete"
EVENT_CHAPTER_FAILED = "chapter_failed"
EVENT_REVIEW_REQUIRED = "review_required"
EVENT_PIPELINE_PROGRESS = "pipeline_progress"
```

### 4.3 Review Policy Manager

**文件**: `Engine/core/review_policy.py`

- **Strict**: 每章 Editor 审核完成后暂停，等待用户审批（通过 API/前端操作）
- **Milestone**: 仅当 RedTeam 发现 Critical 问题或 Review Score < 阈值时中断
- **Headless**: 全自动跑完，不中断，结果记录到日志

**核心接口**:
```python
class ReviewPolicyManager:
    def __init__(self, policy: str = "milestone"):
        ...

    def should_interrupt(self, chapter_result: dict) -> bool:
        """判断是否应该中断 Pipeline 并等待用户审批"""
        ...

    def set_policy(self, policy: str):
        ...
```

### 4.4 Gradient Rewrite Protocol

**修改文件**: `Engine/core/controller.py` (retry 逻辑内)

- **Retry 1 (Patch)**: 只修冲突段落，传入具体冲突位置，LLM 只改写该段
- **Retry 2 (Re-Context)**: 注入精确 State_Snapshot + 冲突详情，要求重写全章
- **Retry 3 (Pivot)**: RedTeam 分析当前失败原因，提出剧情变更建议（如"改为撤退而非战斗"）

**实现方式**: 在 `execute_with_retry` 的每次重试循环中，根据 retry_count 选择不同的策略

### 4.5 MemoryBank 接入 ChromaDB

**修改文件**: `Engine/core/memory_bank.py`

- 当前使用 in-memory 占位，改为接入 ChromaDB
- 支持：add_documents、query_documents（相似度检索）、delete_documents
- 检索结果通过 StateFilter 过滤后注入 Writer 上下文

---

## 5. Phase A: React 前端（P1）

### 5.1 页面结构

```
frontend/src/pages/
├── Workspace.tsx          # 工作台（默认页）— 三栏布局
├── Chapters.tsx           # 章节回顾 — 浏览、搜索、导出
├── Characters.tsx         # 角色管理 — StateDB 查看/编辑
├── Review.tsx             # 评审面板 — 审核意见、通过/驳回
├── SideStory.tsx          # 番外管理 — 生成和浏览番外
├── Projects.tsx           # 项目列表 — 卡片视图、创建/删除
└── Settings.tsx           # 设置 — 模型配置、Pipeline 参数、Daemon、风格克隆
```

### 5.2 工作台页面（Workspace.tsx）

**三栏布局**:

| 左栏（250px） | 中栏（flex-1） | 右栏（300px） |
|---------------|----------------|---------------|
| 章节列表 | 小说正文编辑器 | 角色状态列表 |
| Pipeline 进度条 | Editor 批注叠加层 | 世界状态卡片 |
| [开始生成] 按钮 | Tension 曲线图 | [编辑角色] 按钮 |

**底部状态栏**:
```
Writer: 生成中 65% | Editor: 等待 | RedTeam: 等待 | Token: 12,345
```

### 5.3 API 路由扩展

**修改文件**: `Studio/api.py`

新增端点：
```
POST /api/pipeline/start          # 启动 Pipeline
POST /api/pipeline/stop           # 停止 Pipeline
POST /api/pipeline/review/{approve|reject}  # 审核操作
GET  /api/pipeline/status          # Pipeline 状态
GET  /api/chapters/{id}            # 章节内容
GET  /api/chapters                 # 章节列表（含状态）
PUT  /api/characters/{name}        # 编辑角色状态
GET  /api/settings                 # 获取设置
PUT  /api/settings                 # 更新设置
WS   /ws/pipeline/{project_id}    # WebSocket 实时推送
```

### 5.4 WebSocket 实时推送

**文件**: `Studio/ws.py`

- FastAPI WebSocket 端点
- 订阅 EventBus 事件并推送
- 前端 Zustand store 接收更新

```python
@app.websocket("/ws/pipeline/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await websocket.accept()
    # Subscribe to events and push to client
    ...
```

### 5.5 前端状态管理（Zustand）

```typescript
interface PipelineStore {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  currentChapter: number;
  totalChapters: number;
  agentStatuses: Record<string, AgentStatus>;
  chapters: Chapter[];
  reviewQueue: ReviewItem[];
  settings: Settings;

  // Actions
  startPipeline: () => Promise<void>;
  stopPipeline: () => Promise<void>;
  approveReview: (id: string) => Promise<void>;
  rejectReview: (id: string) => Promise<void>;
  updateSettings: (settings: Partial<Settings>) => Promise<void>;
}
```

---

## 6. 完整功能清单（含 InkOS 对齐）

### 6.1 导入/续写

**文件**: `Engine/core/importer.py`

- 支持导入已有小说（TXT / Markdown / EPUB）
- 自动解析章节结构（按章节标题分割）
- 从 StateDB 重建角色状态和世界状态（反向提取）
- 从指定第 N 章续写（已有章节作为上下文注入 MemoryBank）
- API: `POST /api/import` — 上传文件 + 选择续写起点

**核心接口**:
```python
class NovelImporter:
    def parse_file(self, file_path: str) -> NovelDocument:
        """解析导入文件，返回章节列表和元数据"""
        ...

    def extract_state_from_existing(self, chapters: list[Chapter]) -> dict:
        """从已有章节反向提取角色状态、世界状态"""
        ...

    def resume_from_chapter(self, chapter_num: int, novel: NovelDocument) -> dict:
        """从指定章节续写，返回续写配置"""
        ...

@dataclass
class NovelDocument:
    title: str
    chapters: list[Chapter]
    metadata: dict  # author, genre, created_at, etc.
```

### 6.2 导出功能

**文件**: `Engine/core/exporter.py`

- 支持导出格式：EPUB / TXT / Markdown
- EPUB 生成：封面、目录、章节分页、元数据（标题、作者）
- 导出选项：全部章节 / 指定章节范围 / 仅导出通过审核的章节
- API: `GET /api/export/{format}?chapters=1-30` — 下载文件

**核心接口**:
```python
class NovelExporter:
    def __init__(self, state_db: StateDB):
        ...

    def to_epub(self, chapters: list[Chapter], metadata: dict) -> bytes:
        """生成 EPUB 文件"""
        ...

    def to_txt(self, chapters: list[Chapter]) -> str:
        """生成纯文本"""
        ...

    def to_markdown(self, chapters: list[Chapter]) -> str:
        """生成 Markdown"""
        ...
```

**前端**: Chapters.tsx 页面增加 [导出 EPUB] [导出 TXT] 按钮

### 6.3 题材模板

**文件**: `Engine/configs/genres/`

```
Engine/configs/genres/
├── xuanhuan.yaml        # 玄幻
├── xianxia.yaml         # 仙侠
├── urban.yaml           # 都市
├── scifi.yaml           # 科幻
└── horror.yaml          # 恐怖
```

每个题材模板定义：
- `rules`: 基础写作规则（如玄幻的"战力数值不能倒退"、都市的"使用 2003 年法律术语"）
- `validation`: 校验逻辑（玄幻的"修为等级检查"、恐怖的"氛围递进检查"）
- `ai_filter_words`: 题材特定的 AI 套话禁用词表
- `sensory_requirements`: 感官密度要求（恐怖需要更多听觉/触觉描写）
- `power_system`: 战力体系定义（玄幻的"炼气→筑基→金丹→元婴"）

**题材校验器**: `Engine/core/genre_validator.py`
```python
class GenreValidator:
    def __init__(self, genre_config: dict):
        ...

    def validate_chapter(self, chapter: Chapter, genre: str) -> list[GenreIssue]:
        """根据题材规则校验章节内容"""
        ...
```

**集成点**: Editor Agent 审核时额外运行 GenreValidator
**API**: `GET /api/genres` — 获取可用题材列表，`POST /api/projects` — 创建项目时选择题材

### 6.4 番外/仿写

**文件**: `Engine/agents/side_story.py`, `Engine/agents/imitation.py`

**番外生成**:
- 基于已有角色/世界观生成非主线内容
- 类型：日常篇、前传、后传、角色视角切换
- Prompt 注入：角色 Voice Profile + 番外类型约束
- Pipeline 与主线相同（Writer → Editor → RedTeam），但题材规则放松

**仿写**:
- 导入参考文本（1-3 章），提取统计指纹
- 统计指纹：句式长度分布、段落结构、对话比例、五感描写比例
- Writer Prompt 注入仿写约束："请按照参考文本的风格写作"
- 仿写结果与参考文本做风格相似度评分

**核心接口**:
```python
class SideStoryGenerator:
    def __init__(self, state_db: StateDB, llm_gateway: LLMGateway):
        ...

    def generate(self, side_story_type: str, characters: list[str],
                 word_count: int) -> str:
        """生成番外内容"""
        ...

class ImitationWriter:
    def __init__(self, reference_texts: list[str], llm_gateway: LLMGateway):
        ...

    def extract_style_fingerprint(self) -> dict:
        """提取参考文本的风格指纹"""
        ...

    def write(self, topic: str) -> tuple[str, float]:
        """仿写内容 + 与参考文本的风格相似度 (0-1)"""
        ...
```

**API**: `POST /api/side-story`, `POST /api/imitation`
**前端**: 新增 SideStory.tsx 页面（番外管理）和 Imitation.tsx 页面（仿写工具）

### 6.5 多项目管理

**文件**: `Engine/core/project_manager.py`, `Engine/core/models.py` (新增 Project 模型)

- StateDB 增加 `projects` 表
- 每个项目独立的世界状态、角色列表、章节、配置
- 项目切换时加载对应 StateDB 快照

**Project 模型**:
```python
@dataclass
class Project:
    id: str
    title: str
    genre: str
    total_chapters: int
    current_chapter: int
    status: str  # "draft" | "writing" | "completed" | "paused"
    created_at: str
    updated_at: str
    config: dict  # review_policy, model_overrides, etc.
```

**核心接口**:
```python
class ProjectManager:
    def __init__(self, state_db: StateDB):
        ...

    def create_project(self, title: str, genre: str, total_chapters: int) -> Project:
        ...

    def list_projects(self) -> list[Project]:
        ...

    def get_project(self, project_id: str) -> Project:
        ...

    def switch_project(self, project_id: str):
        ...

    def delete_project(self, project_id: str):
        ...
```

**API**: `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{id}`, `DELETE /api/projects/{id}`
**前端**: Settings 页面增加项目切换器（顶部下拉菜单），新增 Projects.tsx 页面（项目列表卡片视图）

### 6.6 Daemon 模式（后台定时写作）

**文件**: `Engine/core/daemon.py`

- 定时任务调度（cron 表达式）
- 后台运行 Pipeline，不阻塞主进程
- 完成/失败时通过 Webhook / 前端通知告警
- 支持：启动/暂停/停止/查看日志

**核心接口**:
```python
class DaemonScheduler:
    def __init__(self, state_db: StateDB, controller: PipelineController):
        ...

    def schedule(self, project_id: str, cron: str,
                 chapters: tuple[int, int]) -> str:
        """创建定时任务，返回 task_id"""
        ...

    def pause(self, task_id: str):
        ...

    def resume(self, task_id: str):
        ...

    def stop(self, task_id: str):
        ...

    def get_status(self, task_id: str) -> dict:
        ...
```

**API**: `POST /api/daemon/schedule`, `POST /api/daemon/{id}/pause`, `POST /api/daemon/{id}/stop`, `GET /api/daemon/{id}/status`
**前端**: Settings 页面增加 Daemon 控制面板

### 6.7 Token 用量统计

**文件**: `Engine/core/token_tracker.py`

- 每次 LLM 调用记录：model、input_tokens、output_tokens、cost（根据模型定价计算）
- 按章节、按 Agent、按项目汇总
- 前端可视化：每章 Token 柱状图、累计用量曲线、预算告警

**核心接口**:
```python
@dataclass
class TokenUsage:
    chapter: int
    agent: str  # "writer" | "editor" | "redteam" | ...
    model: str
    input_tokens: int
    output_tokens: int
    cost: float  # USD or CNY
    timestamp: str

class TokenTracker:
    def __init__(self, state_db: StateDB):
        ...

    def record(self, usage: TokenUsage):
        ...

    def get_chapter_usage(self, chapter: int) -> list[TokenUsage]:
        ...

    def get_total_usage(self, project_id: str) -> dict:
        """返回 {total_tokens, total_cost, by_agent, by_chapter}"""
        ...

    def get_cost_estimate(self, remaining_chapters: int) -> dict:
        """预估剩余章节的 Token 和费用"""
        ...
```

**API**: `GET /api/tokens/{project_id}` — 获取用量统计，`GET /api/tokens/{project_id}/estimate` — 预估费用
**前端**: 底部状态栏显示累计 Token 和费用，Settings 页面增加预算设置和告警阈值

### 6.8 风格克隆

**文件**: `Engine/llm/style_extractor.py`

- 从参考文本（1-5 章）提取可量化的风格特征
- 特征维度：
  - **句式长度分布**: 平均句长、最长句、最短句、中位数
  - **段落结构**: 平均段落长度、单句段落比例
  - **对话比例**: 对话 vs 叙述的字数比
  - **五感描写比例**: 视觉/听觉/嗅觉/触觉/味觉各占比
  - **形容词密度**: 形容词 / 总词数
  - **修辞手法频率**: 比喻、拟人、排比出现次数
  - **标点偏好**: 感叹号/省略号/破折号使用频率
- 提取结果注入 Writer Prompt 的风格约束

**核心接口**:
```python
@dataclass
class StyleFingerprint:
    avg_sentence_length: float
    avg_paragraph_length: float
    dialogue_ratio: float
    sensory_ratios: dict  # visual: 0.4, auditory: 0.2, ...
    adjective_density: float
    punctuation_ratios: dict

class StyleExtractor:
    def extract(self, text: str) -> StyleFingerprint:
        ...

    def apply_to_prompt(self, fingerprint: StyleFingerprint) -> str:
        """生成风格约束 Prompt"""
        ...
```

**集成点**: PromptBuilder.with_style(fingerprint) 注入风格约束
**API**: `POST /api/style/extract` — 上传参考文本提取风格指纹
**前端**: Settings 页面增加风格克隆面板（上传参考文本 → 显示风格指纹 → 应用到项目）

---

## 7. 错误处理

### 6.1 LLM 层
- **API 限流**: 指数退避重试（1s → 2s → 4s → 8s），最多 5 次
- **超时**: 单请求 60s 超时，超时后重试或降级
- **模型不可用**: 自动 fallback 到下一可用模型

### 6.2 Pipeline 层
- **Agent 卡死**: 看门狗超时（10min）杀掉任务
- **连续失败**: 熔断器（3 次失败后暂停）
- **Token 耗尽**: 优雅降级（降低 Editor 严格度保进度）

### 6.3 前端层
- **WebSocket 断开**: 自动重连（1s → 3s → 5s → 10s），最多 10 次
- **API 错误**: Toast 提示 + 重试按钮
- **审核超时**: 用户长时间不操作，按 Headless 策略继续

---

## 8. 测试策略

### 8.1 单元测试（pytest）
- `tests/llm/test_gateway.py` — LLM 网关（mock API 调用）
- `tests/llm/test_prompt_builder.py` — Prompt 组装
- `tests/llm/test_ai_filter.py` — 去 AI 味检测
- `tests/llm/test_style_extractor.py` — 风格提取
- `tests/core/test_event_bus.py` — 事件总线
- `tests/core/test_review_policy.py` — Review Policy
- `tests/core/test_token_tracker.py` — Token 统计
- `tests/core/test_project_manager.py` — 项目管理
- `tests/core/test_importer.py` — 导入/续写
- `tests/core/test_exporter.py` — 导出功能
- `tests/core/test_daemon.py` — 定时任务
- `tests/core/test_genre_validator.py` — 题材校验
- `tests/agents/test_side_story.py` — 番外生成
- `tests/agents/test_imitation.py` — 仿写

### 8.2 集成测试
- `tests/test_integration.py` — 端到端 Pipeline 测试（mock LLM）
- `tests/studio/test_ws.py` — WebSocket 实时推送测试
- `tests/studio/test_api.py` — 完整 API 端点测试

### 8.3 前端测试
- `frontend/src/__tests__/` — React 组件测试（Vitest + React Testing Library）
- E2E: Playwright 测试关键用户流程

### 8.4 覆盖率目标
- Python: 80%+ line coverage（当前 95%）
- Frontend: 70%+ line coverage

---

## 9. 实现顺序

```
Phase B (LLM 集成) → Phase C (Pipeline 串联) → Phase A (前端) → Phase D (完整功能)

Phase B: LLM Gateway, Prompt Builder, AI Filter, Agent 接入, Voice Profile 增强
Phase C: Pipeline Controller 增强, Event Bus, Review Policy, Gradient Rewrite, ChromaDB
Phase A: React 工作台, WebSocket, 角色管理, 评审面板, 设置
Phase D: 导入/续写, 导出, 题材模板, 番外/仿写, 多项目, Daemon, Token 统计, 风格克隆

理由:
1. Phase B 让 Agent 能真实调用 LLM，是后续所有功能的基础
2. Phase C 让 Pipeline 能串联跑通，产出完整章节
3. Phase A 在前两步基础上加可视化界面
4. Phase D 补充 InkOS 已有但 InkFoundry 需要做得更好的功能
```

每阶段完成后：
- 所有测试通过
- 覆盖率达标
- 可以独立验证（Phase B+C 完成后可以用 CLI 跑完整小说）
