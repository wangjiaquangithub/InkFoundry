# 实现计划：跑通核心工作流

## 目标
让「创建项目 → 生成大纲 → AI逐章生成 → 审核 → 导出」完整跑通，不再依赖 mock 数据。

## 当前问题总结

1. **Pipeline 控制失效**：每次 API 请求创建新的 `PipelineOrchestrator` 实例，pause/resume/stop 操作的是不同实例，无法控制正在运行的流水线
2. **StateFilter/MemoryBank 未接入**：Writer 写章节时不参考历史章节上下文，也不过滤已死角色
3. **ReviewPolicy 未接入**：3种审核模式（strict/milestone/headless）代码写好了但 orchestrator 没调用
4. **Editor arun() 返回固定 score=75**：不管 LLM 回什么，分数都是 75，应从 LLM 返回中解析
5. **批量生成是同步阻塞**：`run_batch` 是 `await` 等全部完成才返回，前端会超时
6. **OutlineAgent arun() 已有**，但 api.py 中 generate_outline 对 JSON 解析错误后回退逻辑脆弱

## 实施计划

### Phase 1: 修复 Pipeline 生命周期（最关键）

**问题**：每次请求新实例 → pause/resume/stop 无效

**方案**：在 api.py 中维护一个全局 `_pipeline_manager` 单例，持有当前正在运行的 orchestrator 和后台 task。

**改动**：
- `Studio/api.py`：新增 `PipelineManager` 类
  - `start_chapter(chapter_num, db)` → 创建 orchestrator + 后台 asyncio task
  - `start_batch(start, end, db)` → 同上
  - `pause()` / `resume()` / `stop()` → 操作同一个 orchestrator 实例
  - `get_status()` → 返回当前 orchestrator 状态
  - `is_running` 属性
- 修改 5 个 pipeline 端点使用 `_pipeline_manager` 而非每次 new
- `POST /api/pipeline/run-chapter/{num}` 变为启动后台任务，立即返回 `{ "started": true }`
- `POST /api/pipeline/run-batch` 同理

### Phase 2: 接入 MemoryBank + StateFilter

**问题**：Writer 不参考历史章节，不过滤已死角色

**方案**：在 orchestrator 的 `run_chapter` 中，Writer 之前：
1. 从 MemoryBank 检索历史章节摘要（最近的 N 章）
2. 通过 StateFilter 过滤掉已死/隐藏角色的上下文
3. 将过滤后的上下文注入 Writer 的 task_card

**改动**：
- `Engine/core/orchestrator.py`：
  - `__init__` 新增 `memory_bank: Optional[MemoryBank]` 参数
  - `run_chapter` 在 Step 2 和 Step 3 之间插入：
    - 查询 MemoryBank 获取历史上下文
    - 用 StateFilter 过滤
    - 将 `filtered_context` 合并进 task_card
  - Step 6 保存章节后，将章节摘要存入 MemoryBank
- `Studio/api.py`：创建 `MemoryBank` 实例传给 orchestrator

### Phase 3: 接入 ReviewPolicy

**问题**：3 种审核模式代码写好了但没调用

**方案**：orchestrator 在 Editor/RedTeam 之后调用 ReviewPolicy.should_interrupt()，决定是否需要暂停等待用户审核。

**改动**：
- `Engine/core/orchestrator.py`：
  - `__init__` 接收 `review_policy: str` 参数
  - `run_chapter` 在步骤 5 之后，调用 `ReviewPolicyManager.should_interrupt()`
  - strict 模式：每章完成后状态设为 "reviewed"，等用户审批
  - milestone 模式：有 critical_issues 时暂停
  - headless 模式：自动设为 "final" 继续下一章
- `Studio/api.py`：从 config 读取 `review_mode` 传给 orchestrator

### Phase 4: 修复 Editor/RedTeam 返回值解析

**问题**：Editor.arun() 返回固定 score=75，未从 LLM 回复解析

**方案**：让 LLM 返回结构化 JSON，解析出 score/issues/feedback。

**改动**：
- `Engine/agents/editor.py`：
  - arun() 的 prompt 要求 LLM 返回 JSON `{"score": 0-100, "issues": [...], "feedback": "..."}`
  - 解析 LLM 返回的 JSON，解析失败回退到 {score: 75, issues: [raw_text]}
- `Engine/agents/redteam.py`：
  - arun() 的 prompt 要求返回 `{"attacks": [...], "severity": "high/medium/low", "feedback": "..."}`
  - 同样解析 JSON

### Phase 5: 修复批量生成不阻塞 API

**问题**：run_batch await 全部完成，前端超时

**方案**：Phase 1 的 PipelineManager 已经解决了——启动后台任务立即返回。

### Phase 6: 端到端验证

- 启动后端 + 前端
- 配置 API Key（Settings 页面）
- 创建项目 → 生成大纲 → 生成第一章 → 审核通过
- 验证 WebSocket 实时推送
- 验证暂停/继续/停止
- 验证批量生成

## 不改的（有意简化）

- DirectorAgent、ImitationAgent、SideStoryAgent：非核心流程，暂不接入 LLM
- VoiceSandbox：作为 prompt 增强工具已实现，但不自动注入到 pipeline（需要手动配置 voice profile）
- ChromaDB：MemoryBank 已支持，没有 chromadb 时自动回退 in-memory，不影响核心流程
- 前端页面结构：暂不重构，先把后端跑通

## 文件改动清单

| 文件 | 改动类型 | 描述 |
|------|---------|------|
| `Studio/api.py` | 修改 | 新增 PipelineManager，修改 5 个 pipeline 端点 |
| `Engine/core/orchestrator.py` | 修改 | 接入 MemoryBank、StateFilter、ReviewPolicy |
| `Engine/agents/editor.py` | 修改 | arun() 解析 LLM 返回的 JSON |
| `Engine/agents/redteam.py` | 修改 | arun() 解析 LLM 返回的 JSON |
| `tests/core/test_orchestrator.py` | 修改 | 新增 MemoryBank/StateFilter/ReviewPolicy 测试 |
| `tests/studio/test_api.py` | 修改 | 新增 PipelineManager 测试 |
