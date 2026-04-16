# InkFoundry 完整系统设计 Spec v2

> **Goal**: 构建一个功能全面超越 InkOS、使用简单、输出高质量的 AI 长篇小说全自动生成系统。
>
> **Design Philosophy**: 三步开始写作，渐进式复杂度，质量优先。
>
> **Architecture**: 双引擎架构 — Python Engine（执行层）+ React Studio（可视化控制层）
>
> **Tech Stack**: Python (FastAPI, SQLite, Pydantic, openai, chromadb) + React (Vite, shadcn/ui, Tailwind CSS, Zustand, WebSocket)

---

## 1. 设计原则

### 1.1 使用简单

- **三步开始写作**：用户只需要 3 步就能让系统开始自动生成小说
  1. 选题材、填标题、写简介、设章数 → 点"开始"
  2. 系统自动生成大纲、角色、世界观 → 用户审核/调整
  3. 点"开始写作"→ 自动逐章生成
- **渐进式复杂度**：默认极简，高级功能可深入
  - **默认模式**：3 步开始，自动运行
  - **进阶模式**：调整大纲、编辑角色、修改世界观
  - **专家模式**：调整 Agent 参数、模型路由、Review Policy
- **不需要用户做技术决策**：模型选择有默认值、参数有合理预设

### 1.2 功能完善

- 从立项到导出，全流程覆盖
- 每个环节都有，不缺失关键环节
- 高级功能在"设置"或"高级"面板中，不影响新手体验

### 1.3 高质量内容

- **大纲质量**：基于题材生成完整故事结构（起承转合、分卷规划、张力曲线）
- **角色质量**：自动生成人物小传 + 关系图 + Voice Profile
- **章节质量**：多 Agent 审核（Writer → Editor → RedTeam → 梯度重写）
- **一致性质量**：StateDB 是唯一真相源，阻断矛盾
- **风格质量**：风格克隆 + Voice Profile 确保文风一致

---

## 2. 系统架构

### 2.1 数据层（新增）

```
StateDB 新增表：
├── projects              # 项目元数据（已有，需完善）
├── outlines              # [新增] 大纲：主线、分卷、章节概要、伏笔
├── chapters              # [新增] 章节：内容、状态、版本、审核意见
├── chapter_versions      # [新增] 章节版本历史
├── characters            # 角色（已有，需扩展）
├── character_profiles    # [新增] 角色详细资料：外貌、性格、背景、动机
├── character_relationships # [新增] 角色关系：类型、描述、强度
├── world_states          # 世界状态（已有）
├── world_building        # [新增] 世界观详细设定：力量体系、地理、时间线
├── power_systems         # [新增] 力量体系：修炼等级、规则
├── timelines             # [新增] 时间线：重大事件年表
├── snapshots             # 快照（已有）
├── token_usage           # [新增] Token 使用记录
├── review_queue          # [新增] 审核队列（Strict 模式）
└── daemon_tasks          # [新增] Daemon 定时任务
```

### 2.2 Engine 层（新增 + 修改）

**新增文件**：
| 文件 | 用途 |
|------|------|
| `Engine/agents/outline.py` | 大纲生成 Agent |
| `Engine/core/orchestrator.py` | 管线编排器（串联所有 Agent） |

**修改文件**：
| 文件 | 修改内容 |
|------|----------|
| `Engine/core/models.py` | 新增 Outline, Chapter, CharacterProfile, WorldBuilding 等 Pydantic 模型 |
| `Engine/core/state_db.py` | 新增 10+ 张表 |
| `Engine/core/controller.py` | 新增 `run_chapter()`, `run_batch()`, `pause()`, `resume()`, `stop()` |
| `Engine/agents/navigator.py` | 改为基于大纲生成 TaskCard |
| `Engine/agents/writer.py` | `run()` 改为调 `arun()` 或新增统一入口 |
| `Engine/agents/editor.py` | 同上 |
| `Engine/agents/redteam.py` | 同上 |

### 2.3 API 层（新增端点）

```
# 项目
POST /api/projects              # 创建项目
GET  /api/projects              # 项目列表
GET  /api/projects/{id}         # 项目详情
PUT  /api/projects/{id}         # 更新项目
DELETE /api/projects/{id}       # 删除项目

# 大纲
POST /api/projects/{id}/outline/generate  # 生成大纲
GET  /api/projects/{id}/outline           # 获取大纲
PUT  /api/projects/{id}/outline           # 修改大纲

# 角色
POST   /api/projects/{id}/characters              # 创建角色
GET    /api/projects/{id}/characters              # 角色列表
GET    /api/projects/{id}/characters/{name}        # 角色详情
PUT    /api/projects/{id}/characters/{name}        # 更新角色
DELETE /api/projects/{id}/characters/{name}        # 删除角色
POST   /api/projects/{id}/characters/relationships # 创建角色关系

# 世界观
POST /api/projects/{id}/world-building       # 创建世界观
GET  /api/projects/{id}/world-building       # 获取世界观
PUT  /api/projects/{id}/world-building       # 更新世界观

# 章节
GET    /api/projects/{id}/chapters           # 章节列表
GET    /api/projects/{id}/chapters/{num}     # 章节内容
PUT    /api/projects/{id}/chapters/{num}     # 编辑章节
DELETE /api/projects/{id}/chapters/{num}     # 删除章节
GET    /api/projects/{id}/chapters/{num}/versions  # 版本历史
POST   /api/projects/{id}/chapters/{num}/rollback  # 回滚版本

# Pipeline 控制
POST /api/projects/{id}/pipeline/start      # 启动 Pipeline
POST /api/projects/{id}/pipeline/stop       # 停止 Pipeline
POST /api/projects/{id}/pipeline/pause      # 暂停
POST /api/projects/{id}/pipeline/resume     # 继续
GET  /api/projects/{id}/pipeline/status     # Pipeline 状态

# 审核
GET  /api/projects/{id}/reviews             # 待审核列表
POST /api/projects/{id}/reviews/{id}/approve  # 通过
POST /api/projects/{id}/reviews/{id}/reject   # 驳回

# 导入/导出
POST /api/projects/{id}/import              # 导入/续写
GET  /api/projects/{id}/export/{format}     # 导出
GET  /api/projects/{id}/export/{format}?chapters=1-30

# 设置
GET  /api/projects/{id}/settings            # 获取设置
PUT  /api/projects/{id}/settings            # 更新设置

# Token 统计
GET  /api/projects/{id}/tokens              # Token 用量
GET  /api/projects/{id}/tokens/estimate     # 预估费用

# 风格克隆
POST /api/projects/{id}/style/extract       # 提取风格
POST /api/projects/{id}/style/apply         # 应用风格

# 番外/仿写
POST /api/projects/{id}/side-story          # 生成番外
POST /api/projects/{id}/imitation           # 仿写

# Daemon
POST /api/projects/{id}/daemon/schedule     # 创建定时任务
GET  /api/projects/{id}/daemon/{task_id}    # 任务状态
POST /api/projects/{id}/daemon/{task_id}/pause  # 暂停任务
POST /api/projects/{id}/daemon/{task_id}/stop   # 停止任务

# WebSocket
WS   /ws/projects/{id}                     # 实时推送
```

### 2.4 前端层（7 个页面）

```
frontend/src/pages/
├── CreateProject.tsx    # [新增] 创建项目页 — 3 步向导
├── Projects.tsx         # [新增] 项目列表 — 卡片视图
├── Workspace.tsx        # [改造] 工作台 — 完整版（章节列表 + 编辑器 + 实时状态）
├── Outline.tsx          # [新增] 大纲管理 — 查看/编辑/重新生成
├── Chapters.tsx         # [新增] 章节回顾 — 浏览/搜索/导出/版本对比
├── Characters.tsx       # [新增] 角色管理 — 完整 CRUD + 关系图 + 人物小传
├── WorldBuilder.tsx     # [新增] 世界观 — 力量体系 + 地理 + 时间线
├── Review.tsx           # [新增] 审核面板 — 审核意见 + 通过/驳回
└── Settings.tsx         # [新增] 设置 — 模型配置 + Daemon + 风格克隆 + Token
```

### 2.5 前端组件

```
frontend/src/components/
├── ChapterEditor.tsx          # 章节编辑器（富文本 + 保存 + 版本切换）
├── CharacterRelations.tsx     # 角色关系图可视化
├── WorldBuilderForm.tsx       # 世界观编辑器
├── PipelineStatusBar.tsx      # Pipeline 底部状态栏
├── TensionGraph.tsx           # 张力曲线图
├── TokenChart.tsx             # Token 用量图
├── StyleFingerprint.tsx       # 风格指纹展示
├── ReviewCard.tsx             # 审核卡片组件
└── ProjectCard.tsx            # 项目卡片组件
```

---

## 3. 用户体验流程

### 3.1 三步开始写作

**第一步：创建项目**
- 用户进入创建项目页，填写：
  - 题材（下拉：玄幻/仙侠/都市/科幻/武侠）
  - 标题
  - 简介（1-3 句话描述故事）
  - 目标章数（默认 100）
  - 每章字数（默认 3000）
- 点"开始"→ 系统进入第二步

**第二步：生成大纲**
- 系统自动调用 OutlineAgent 生成：
  - 故事主线（起承转合）
  - 分卷规划
  - 章节概要（每章一句话概述）
  - 张力曲线预设
- 自动生成初始角色（主角、主要配角、反派）
- 自动生成世界观框架（根据题材）
- 用户查看大纲、角色、世界观
- 可以调整，也可以点"确认"进入第三步

**第三步：开始写作**
- 用户点"开始写作"
- 系统自动运行 Pipeline：
  ```
  Navigator → Writer(LLM) → Editor(LLM) → RedTeam(LLM) → 保存
  ```
- 前端实时显示：
  - 当前 Agent 在做什么（Writer 生成中 65%）
  - 章节进度
  - Token 消耗
- 任何时刻可以：暂停、继续、跳过、调整

### 3.2 章节生成流程（自动化）

每章生成经过以下步骤：

```
1. Navigator 读取大纲第 N 章概要 → 生成 TaskCard（张力、线索、伏笔）
2. MemoryBank 回忆历史章节 → StateFilter 过滤矛盾
3. Writer 基于 TaskCard + 记忆 + Voice + 世界观 → 生成草稿
4. Editor 审核：逻辑检查 + 风格检查 + AI味检测 + 题材校验 → 打分
5. RedTeam 攻击：剧情合理性、角色一致性、世界观一致性 → 找漏洞
6. 如果 score >= 85 → 保存章节 → 更新 StateDB → 通知前端 → 下一章
7. 如果 score < 85 且 retry < 3 → GradientRewrite 修正 → 回到步骤 4
8. 如果 retry == 3 → 优雅降级（降低标准，保存进度）→ 记录到审核队列
```

### 3.3 人工审核流程（Strict 模式）

```
1. 章节完成（或降级保存）后，进入审核队列
2. 前端 Review 页面显示：
   - 章节内容
   - Editor 审核意见（问题列表 + 评分）
   - RedTeam 攻击结果（漏洞列表）
   - AIFilter 检测结果
3. 用户操作：
   - 通过 → 章节标记为 final → 下一章
   - 驳回 → 章节标记为 rejected → 用户可修改或重新生成
   - 修改 → 用户直接编辑章节内容 → 保存 → 下一章
```

### 3.4 高级模式

- **调整大纲**：在 Outline 页面修改章节概要，影响后续章节生成
- **编辑角色**：在 Characters 页面修改人物小传、关系、Voice Profile
- **修改世界观**：在 WorldBuilder 页面修改力量体系、地理、时间线
- **调整模型**：在 Settings 页面为不同 Agent 配置不同模型
- **设置 Daemon**：在 Settings 页面设置定时自动生成（如每天写 3 章）

---

## 4. 高质量保障体系

### 4.1 大纲质量

- **故事结构**：起承转合四阶段，每阶段有明确目标
- **分卷规划**：每卷有独立主题和冲突
- **章节概要**：每章一句话概述，确保剧情连贯
- **张力曲线**：高潮→平缓→高潮，避免平铺直叙
- **伏笔管理**：埋设→追踪→揭示，避免遗漏

### 4.2 角色质量

- **人物小传**：外貌特征、性格特点、背景故事、目标动机
- **角色关系**：父子/师徒/仇敌/恋人，带关系强度和描述
- **Voice Profile**：说话习惯、口头禅、禁用词、感官偏好
- **角色弧线**：从起点到终点的成长轨迹

### 4.3 章节质量

| 检查项 | 负责 Agent | 检查内容 |
|--------|-----------|----------|
| 逻辑一致性 | Editor | 角色行为是否符合设定、剧情是否连贯 |
| 风格一致性 | Editor + AIFilter | 文风是否符合题材、AI套话检测 |
| 剧情合理性 | RedTeam | 剧情是否有漏洞、动机是否合理 |
| 角色一致性 | Editor + VoiceSandbox | 角色说话是否符合 Voice Profile |
| 世界观一致性 | Editor + StateFilter | 是否符合世界观设定、是否与 StateDB 矛盾 |
| 题材规则 | GenreValidator | 是否符合题材写作规则 |
| 感官密度 | AIFilter | 五感描写是否充足 |

### 4.4 一致性保障

- **StateDB 是唯一真相源**：角色状态、世界观以 StateDB 为准
- **State-Over-Vector Filter**：RAG 结果与 StateDB 矛盾时，以 StateDB 为准
- **章节版本管理**：每次修改保存版本，可随时回滚
- **快照管理**：每章完成后自动保存快照

### 4.5 风格质量

- **风格克隆**：从参考文本提取风格指纹，应用到全书
- **Voice Profile**：每个角色有独特说话方式
- **题材模板**：不同题材有不同写作规则约束
- **AIFilter**：检测并去除 AI 套话、重复句式

---

## 5. 实现顺序

```
Phase 0：数据地基（1-2 天）
  ├── 新增 10+ 张 StateDB 表
  ├── 新增 Pydantic 模型
  └── 测试 + 覆盖率 80%+

Phase 1：核心管线（3-5 天）
  ├── 大纲系统（OutlineAgent + API + UI）
  ├── 管线编排器（PipelineOrchestrator）
  ├── 章节存储 + CRUD API
  ├── Agent 真实 LLM 调用
  ├── WebSocket 真实事件推送
  └── 测试 + 覆盖率 80%+

Phase 2：完整前端（3-5 天）
  ├── 创建项目页（3 步向导）
  ├── 项目列表页
  ├── 工作台（完整版）
  ├── 大纲管理页
  ├── 章节回顾页
  ├── 角色管理（完整版 + 关系图）
  ├── 世界观管理页
  ├── 审核面板
  ├── 设置页
  └── 测试

Phase 3：增值功能（3-5 天）
  ├── 导入/导出
  ├── 多项目管理
  ├── Daemon 自动写作
  ├── Token 统计
  ├── 风格克隆
  ├── 番外/仿写
  └── 题材模板 UI
```

**每 Phase 交付标准**：
- Engine 代码 + 测试（80%+ 覆盖率）
- API 端点 + 测试
- 前端页面 + 功能
- 端到端可验证

---

## 6. 错误处理

| 层级 | 错误类型 | 处理方式 |
|------|----------|----------|
| LLM 层 | API 限流 | 指数退避重试（1s→2s→4s→8s），最多 5 次 |
| LLM 层 | 超时 | 60s 超时，超时后重试或降级 |
| LLM 层 | 模型不可用 | 自动 fallback 到下一可用模型 |
| Pipeline 层 | Agent 卡死 | 看门狗超时（10min）杀掉任务 |
| Pipeline 层 | 连续失败 | 熔断器（3 次失败后暂停） |
| Pipeline 层 | Token 耗尽 | 优雅降级（降低 Editor 严格度保进度） |
| 前端层 | WebSocket 断开 | 自动重连（1s→3s→5s→10s），最多 10 次 |
| 前端层 | API 错误 | Toast 提示 + 重试按钮 |
| 审核层 | 用户长时间不操作 | 按 Headless 策略继续 |

---

## 7. 竞品对比（vs InkOS）

| 维度 | InkOS | InkFoundry | 优势 |
|------|-------|------------|------|
| 状态管理 | 7 个 Truth Files（JSON） | StateDB（SQLite 原子操作、版本并发、快照回滚） | 数据库级一致性 |
| 大纲生成 | 无 | OutlineAgent + 故事结构 + 分卷规划 | 有规划，不盲写 |
| 章节存储 | Truth Files | StateDB chapters 表 + 版本管理 | 可回滚，可对比 |
| 角色管理 | 基础 | 人物小传 + 关系图 + Voice Profile | 人物立体 |
| 矛盾处理 | Auditor 检测 → revise | State-Over-Vector Filter（硬过滤） | 矛盾直接阻断 |
| 重试策略 | 无限 revise | 梯度重写（Patch → Re-Context → Pivot） | 不浪费 Token |
| 人工控制 | 单一模式 | 三种策略（Strict / Milestone / Headless） | 灵活 |
| 自动化 | 手动 | Daemon 定时自动写作 | 无人值守 |
| 前端 | CLI + 基础 Web | 7 个页面 + 实时推送 + 富文本编辑 | 体验好 |
| Token 统计 | 无 | 按章节/Agent 统计 + 费用预估 | 成本可控 |

---

## 8. 测试策略

### 8.1 单元测试（pytest）

- `tests/agents/test_outline.py` — 大纲生成 Agent
- `tests/core/test_orchestrator.py` — 管线编排器
- `tests/core/test_chapters.py` — 章节 CRUD
- `tests/core/test_character_relationships.py` — 角色关系
- `tests/core/test_world_building.py` — 世界观
- 现有测试全部更新以适配新数据模型

### 8.2 集成测试

- `tests/test_integration.py` — 端到端 Pipeline 测试（mock LLM）
- `tests/studio/test_api.py` — 完整 API 端点测试
- `tests/studio/test_ws.py` — WebSocket 实时推送测试

### 8.3 覆盖率目标

- Python: 80%+ line coverage
- Frontend: 70%+ line coverage
