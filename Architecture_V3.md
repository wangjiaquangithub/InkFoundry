# AI 长篇小说工厂架构 v3.0 (Universal AI Novel Factory)

> **设计目标**：解决长篇小说量产中的“逻辑崩坏”、"AI 味重”、“上下文失忆”和“系统卡死”四大痛点，实现**高保真、全自动、抗衰减**的工业化内容生产。

---

## 🏗️ 一、 物理目录结构

系统分为**引擎层**（通用代码/Agent 逻辑）和**实例层**（具体小说数据），支持无限扩展新小说。

```text
/Users/wangjiaquan/project/demo/inkos/novels/
├── 📂 Engine/                 # 【通用核心引擎】(Agent Logic & Infrastructure)
│   ├── 📂 agents/             
│   │   ├── writer.py          # 写手 (支持混合模型路由，角色语音注入)
│   │   ├── editor.py          # 审稿 (双盲校验：逻辑 + 文风)
│   │   ├── redteam.py         # 红队 (对抗找茬、防平庸、压力测试)
│   │   └── navigator.py       # 导航仪 (节奏控制、钩子设计、爽点热力图)
│   ├── 📂 core/               
│   │   ├── state_db.py        # StateDB (SQLite + MCP Server, 原子锁/快照)
│   │   ├── memory_bank.py     # Vector Memory (RAG 长文召回)
│   │   └── controller.py      # Pipeline Controller (看门狗、熔断、防死锁)
│   ├── 📂 templates/          # 题材模板库 (玄幻/都市/科幻配置)
│   └── 📂 utils/              # 工具脚本 (去 AI 味、格式校验)
│
└── 📂 Projects/               # 【小说实例目录】
    └── 📂 <Project_ID>/       # 例如：novel_001_changsheng
         ├── 📄 config.yaml          # 项目配置 (模型路由、题材、目标字数)
         ├── 📂 01_State/            # 动态状态数据库 (核心真理)
         │    ├── 📄 state.db        # SQLite (支持因果图、行锁)
         │    └── 📁 snapshots/      # 状态快照 (用于崩溃回滚)
         ├── 📂 02_Outlines/         # 导航产出 (骨架)
         │    ├── 📄 volume_01.md    # 第一卷宏观大纲
         │    └── 📂 chapters/       # 每章任务卡 (Task Card)
         ├── 📂 03_Archives/         # 历史档案馆 (记忆)
         │    ├── 📄 summaries.json  # 剧情摘要 (滚动加载)
         │    └── 📁 vector_db/      # 向量索引 (用于长文精准召回)
         └── 📂 04_Chapters/         # 正文产出
              ├── 📄 0001_draft.md  # 草稿 (Writer)
              ├── 📄 0001_review.md # 审稿报告 (Editor/RedTeam)
              └── 📄 0001_final.md  # 定稿
```

---

## 🔄 二、 核心数据流 (协同网模式)

不再是单向流水线，而是**“对抗 + 反馈 + 记忆”**的动态闭环。

```text
[1. 导航] Navigator 生成 Chapter_N 任务卡 (定义爽点、冲突、钩子、Tension_Level)
   ↓
[2. 召回] MemoryBank (RAG) 召回历史伏笔 + StateDB 读取当前状态 (人物/物品)
   ↓
[3. 撰写] WriterAgent 结合任务卡 + 记忆 + 角色语音包 -> 生成 Draft_v1
   ↓
[4. 对抗] EditorCritic + RedTeamAgent 联合审查
   ├── 🔍 Logic Check：查 OOC、吃书、逻辑断裂
   ├── 🎨 Style Check：查 AI 味、句式重复、感官缺失
   └── ⚔️ RedTeam：恶意攻击剧情合理性 (寻找漏洞)
   ↓
   ❌ 如果未达标 (Score < 85 且 重试次数 < 3)
      ↩️ 返回 Writer，附带 Patch_Instructions (修改指令) -> 生成 Draft_v2
   ↓
   ✅ 如果达标 OR 触发熔断 (重试 == 3)
      ↓
[5. 归档] StateDB.update_state (更新人物、物品、伏笔状态 - 带原子锁)
   ↓
[6. 存储] 保存 Final.md -> 压缩摘要存入 Archives -> 触发下一章
```

---

## 🛡️ 三、 关键机制设计

### **1. 防死锁与熔断机制 (Anti-Deadlock)**
*   **Max-Retry = 3**：任何章节重写超过 3 次，Pipeline 强制介入。
*   **降级妥协 (Graceful Degradation)**：Controller 降低 Editor 严格度，允许“小瑕疵”存在，优先保住进度，将问题记录入 `known_issues.json` 待后续剧情修复。
*   **看门狗 (Watchdog)**：每个任务强制超时 (如 10 分钟)。超时直接 Kill + 清理现场 + 降级重试，绝不干等。

### **2. StateDB 进化：因果图谱与原子性**
*   **MCP Tool 封装**：Agent 通过标准接口 (`read_state`, `update_state`, `rollback`) 操作数据库，彻底解耦。
*   **写时锁 (Write Lock)**：Writer 和 Editor 竞争状态更新时，确保不冲突，防止数据损坏。
*   **快照回滚 (Snapshot)**：每章定稿自动备份 State。若第 N 章逻辑彻底崩坏，可一键回滚至 `Snapshot_N-1`。
*   **Causality Graph**：记录“伏笔”与“回收”的连接。示例：`H01 (玉佩) -> 影响节点 (Ch50 开启古阵)`。

### **3. 混合模型路由 (Cost & Quality)**
*   在 `config.yaml` 中动态定义路由规则：
    *   **Writing (日常)**：`Qwen-Plus` (快、成本低)。
    *   **Writing (高潮)**：`Claude-3.5-Sonnet` (强逻辑、好文笔)。
    *   **Critic (审稿)**：`DeepSeek-R1` (强推理、查逻辑)。

### **4. 质量控制 (Quality Control)**
*   **角色语音实验室 (Voice Sandbox)**：独立维护 `voice_profiles.yaml`，强制约束对话风格（口头禅、句式长短），防止角色同质化。
*   **爽点热力图 (Tension Heatmap)**：导航仪监控 `Tension_Level`。若连续 3 章低分，强制下一章生成“高冲突任务”。
*   **去 AI 味策略 (Anti-AI)**：
    *   **感官校验**：强制要求每章包含非视觉描写（听觉/嗅觉/触觉）。
    *   **动态禁词表**：自动统计并禁用 AI 高频词（如“不可置信”、“仿佛”）。

---

## 🚀 四、 下一步执行计划

1.  **Phase 0 (MVP)**：搭建 `Engine` 核心结构，实现 StateDB (MCP 版) 和 Controller 基础逻辑。
2.  **Phase 1**：跑通 Writer -> Editor 的反馈循环，完成《长生》项目初始化。
3.  **Phase 2**：引入 RedTeam 和 MemoryBank (RAG)，强化长文逻辑。

**架构已锁定，随时准备进入代码实现阶段。**
