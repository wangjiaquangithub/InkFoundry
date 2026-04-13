# InkFoundry Architecture v3.2 (Narrative OS Blueprint)

> **Project**: InkFoundry  
> **Concept**: Narrative OS — A Dual-Layer System combining **Industrial Automation (Engine)** with **Visual Insight (Studio)**.  
> **Goal**: Solve "logic collapse", "AI flavor", "context amnesia", and "system deadlock" in mass-producing long-form novels.

---

## 🏛️ 1. System Topology (Dual-Layer Architecture)

The system is divided into the **Execution Engine** (Power) and the **Command Surface** (Vision).

```text
InkFoundry /
├── 📂 Engine/                 # [Layer 1: Execution Engine]
│   ├── 📂 agents/             
│   │   ├── writer.py          # Writer Agent (Drafting, Style injection)
│   │   ├── editor.py          # Editor Agent (Logic & Style Check)
│   │   ├── redteam.py         # RedTeam Agent (Adversarial testing, Plot attack)
│   │   └── navigator.py       # Navigator Agent (Pacing, Hooks, Task Cards)
│   │   └── director.py        # Director Agent (Controls Role-Play Sandbox)
│   ├── 📂 core/               
│   │   ├── state_db.py        # StateDB (SQLite + MCP Server, Atomic locks/Snapshots)
│   │   ├── memory_bank.py     # Vector Memory (RAG + State_Filter)
│   │   └── controller.py      # Pipeline Controller (Watchdog, Circuit Breaker)
│   ├── 📂 templates/          # Genre Templates (Config & Prompts)
│   └── 📂 utils/              # Anti-AI filters, Formatting checks
│
└── 📂 Studio/                 # [Layer 2: Command Surface / UI]
    ├── 📂 dashboard/          # Visualizations (Tension Heatmap, Causality Graph)
    ├── 📂 editor/             # Manual Intervention & Chapter Editing
    └── 📂 sandbox/            # Role-Play Arena for Agents
```

---

## 🔄 2. Core Data Flow (Collaborative Network)

A dynamic loop of **Adversarial Generation + State Synchronization**.

```text
[1. Navigation] Navigator generates Chapter_N Task Card (Tension, Hooks, Clues)
   ↓
[2. Recall] MemoryBank (RAG) -> passes through State_Filter -> injects Context
   ↓
[3. Writing] WriterAgent combines Task Card + Memory + Voice Profile -> Draft_v1
   ↓
[4. Adversarial Review] Editor + RedTeam Joint Review
   ├── 🔍 Logic Check: OOC, continuity, logic gaps (StateDB vs RAG)
   ├── 🎨 Style Check: AI flavor, sensory details, pacing
   └── ⚔️ RedTeam: Maliciously attacks plot rationality (Finding loopholes)
   ↓
   ❌ If Score < 85 AND Retries < 3 -> [Gradient Rewrite Protocol] -> Draft_v2
   ↓
   ✅ If Pass OR Circuit Breaker Triggered (Retries == 3)
      ↓
[5. Archiving] StateDB.update_state (Atomic Lock applied)
   ↓
[6. Storage] Save Final.md -> Sync State to Studio -> Trigger Next Chapter
```

---

## 🛡️ 3. Key Mechanisms Design

### **3.1 Anti-Deadlock & Circuit Breaker Protocol**
*   **Max-Retry = 3**: If a chapter is rewritten > 3 times, Pipeline forces intervention.
*   **Watchdog**: Hard timeout (e.g., 10 mins) per task. Timeout -> Kill -> Clean -> Downgrade/Retry.
*   **Graceful Degradation**: Controller lowers Editor strictness on Retry 3 to save progress.

### **3.2 StateDB Evolution: Causality & Atomicity**
*   **MCP Tool Encapsulation**: Agents operate via standard interfaces (`read_state`, `update_state`, `rollback`).
*   **Write Lock**: Prevents conflict when Writer and Editor compete for state updates.
*   **Snapshot Rollback**: Auto-backup state after each chapter. Instant rollback to `Snapshot_N-1`.

### **3.3 Advanced Logic: Memory & Conflict Resolution (v3.1 Patch)**
*   **State-Over-Vector Filter (Hard Truth Filter)**: 
    *   **Mechanism**: RAG results pass through a `State_Filter` before injection.
    *   **Logic**: If RAG recalls "Character A is alive" but `StateDB` says "Character A died", the filter **blocks the RAG result**. StateDB is the single source of truth.
*   **Gradient Rewrite Protocol (Smart Recovery)**:
    *   **Retry 1 (Patch)**: Localized fix. Only rewrite the conflicting paragraph.
    *   **Retry 2 (Re-Context)**: Inject precise `State_Snapshot` to force re-evaluation.
    *   **Retry 3 (Pivot Strategy)**: **Ultimate Fallback**. RedTeam proposes a **Plot Change** (e.g., "Change mission: retreat instead of fight"). Kills infinite loops.

---

## ⚙️ 4. Operational Flexibility (User Control)

### **4.1 Review Policy Matrix (Human-in-the-Loop)**
*   **Strict Mode**: User approves every chapter. (High Quality Control)
*   **Milestone Mode**: AI runs autonomously. Interrupts only on **Logic Branches** or **RedTeam Critical Alerts**. (Balanced)
*   **Headless Mode**: Fire-and-forget automation. (Speed)

### **4.2 Hierarchical Model Routing**
*   **L1 Global Default**: Base model for the whole project (e.g., `Qwen-Plus`).
*   **L2 Agent Override**: Assign specific models to Agents (e.g., Editor uses `Claude` for reasoning).
*   **L3 Task Override**: Temporary upgrade for specific tasks (e.g., Climax chapters use `Opus`).

---

## 🎭 5. Creative Sandbox (Agent Symbiosis)

### **5.1 Director_Agent (The Brain)**
*   **Role**: Controls the Role-Play Sandbox to prevent infinite loops or "happy talk".
*   **Mechanism**: 
    *   Injects **Event Pressure** (e.g., "Police sirens heard outside") to force character decisions.
    *   Enforces character consistency.
*   **Output**: Generates a `Decision_Log` (e.g., "Protagonist decides to sacrifice Item A"), which Navigator converts into the next `Task_Card`.

---

## 🚀 6. Execution Plan

1.  **Phase 0 (MVP)**: Build `Engine` core structure, implement StateDB (MCP) and Controller base logic.
2.  **Phase 1**: Run Writer -> Editor feedback loop, initialize first project (InkFoundry Core).
3.  **Phase 2**: Introduce RedTeam, MemoryBank (RAG), and Sandbox features.
4.  **Phase 3**: Connect Studio Interface (Visualization & Manual Intervention).

**Architecture locked. Ready for implementation.**
