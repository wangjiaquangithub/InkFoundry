# InkFoundry Architecture v3.0 (AI Novel Factory)

> **Project Name**: InkFoundry  
> **Design Goal**: To solve "logic collapse", "AI flavor", "context amnesia", and "system deadlock" in mass-producing long-form novels. Achieve **high-fidelity, fully automated, anti-decay** industrial content production.

---

## 🏗️ 1. Physical Directory Structure

The system is divided into the **Engine Layer** (Common Code/Agent Logic) and the **Instance Layer** (Specific Novel Data), supporting infinite expansion for new novels.

```text
/InkFoundry/
├── 📂 Engine/                 # Core Engine
│   ├── 📂 agents/             
│   │   ├── writer.py          # Writer Agent (Multi-model routing, Voice Profile injection)
│   │   ├── editor.py          # Editor Agent (Dual-blind review: Logic + Style)
│   │   ├── redteam.py         # RedTeam Agent (Adversarial testing, Anti-cliché)
│   │   └── navigator.py       # Navigator Agent (Pacing, Hooks, Tension Heatmap)
│   ├── 📂 core/               
│   │   ├── state_db.py        # StateDB Core (SQLite + MCP Server, Atomic locks/Snapshots)
│   │   ├── memory_bank.py     # Vector Memory (RAG for long-context recall)
│   │   └── controller.py      # Pipeline Controller (Watchdog, Circuit Breaker, Anti-deadlock)
│   ├── 📂 templates/          # Genre Templates (Xuanhuan/Urban/Sci-Fi configs)
│   └── 📂 utils/              # Utils (Anti-AI filters, Formatting checks)
│
└── 📂 Projects/               # Project Instances
    └── 📂 <Project_ID>/       # e.g., novel_001_longevity
         ├── 📄 config.yaml          # Project Config (Model routing, Genre, Word count)
         ├── 📂 01_State/            # Dynamic State Database (Single Source of Truth)
         │    ├── 📄 state.db        # SQLite (Causality Graph, Row-level locks)
         │    └── 📁 snapshots/      # State Snapshots (For crash rollback)
         ├── 📂 02_Outlines/         # Navigation Output (Skeleton)
         │    ├── 📄 volume_01.md    # Volume Macro-Outline
         │    └── 📂 chapters/       # Chapter Task Cards (Micro-Outline)
         ├── 📂 03_Archives/         # History Archives (Memory)
         │    ├── 📄 summaries.json  # Chapter Summaries (Rolling context window)
         │    └── 📁 vector_db/      # Vector Index (Semantic retrieval for long context)
         └── 📂 04_Chapters/         # Chapter Output
              ├── 📄 0001_draft.md  # Draft (From Writer)
              ├── 📄 0001_review.md # Review Report (From Editor/RedTeam)
              └── 📄 0001_final.md  # Final Version
```

---

## 🔄 2. Core Data Flow (Collaborative Network)

不再是单向流水线，而是**“对抗 + 反馈 + 记忆”**的动态闭环。

```text
[1. Navigation] Navigator generates Chapter_N Task Card (Defines Tension, Hooks, Clues)
   ↓
[2. Recall] MemoryBank (RAG) recalls historical foreshadowing + StateDB reads current state
   ↓
[3. Writing] WriterAgent combines Task Card + Memory + Voice Profile -> Generates Draft_v1
   ↓
[4. Adversarial Review] EditorCritic + RedTeamAgent Joint Review
   ├── 🔍 Logic Check: OOC, continuity breaks, logic gaps
   ├── 🎨 Style Check: AI flavor, repetitive sentences, lack of sensory details
   └── ⚔️ RedTeam: Maliciously attacks plot rationality (Finding loopholes)
   ↓
   ❌ If Score < 85 AND Retries < 3
      ↩️ Return to Writer with Patch_Instructions -> Generate Draft_v2
   ↓
   ✅ If Pass OR Circuit Breaker Triggered (Retries == 3)
      ↓
[5. Archiving] StateDB.update_state (Update characters, items, foreshadowing status with Atomic Lock)
   ↓
[6. Storage] Save Final.md -> Compress summary to Archives -> Trigger Next Chapter
```

---

## 🛡️ 3. Key Mechanisms Design

### **1. Anti-Deadlock & Circuit Breaker Protocol**
*   **Max-Retry = 3**: If a chapter is rewritten more than 3 times, Pipeline forces intervention.
*   **Graceful Degradation**: Controller lowers Editor strictness, allows "minor flaws" to save progress, logging issues to `known_issues.json` for future fixes.
*   **Watchdog**: Hard timeout (e.g., 10 mins) per task. Timeout -> Kill -> Clean -> Retry/Downgrade.

### **2. StateDB Evolution: Causality & Atomicity**
*   **MCP Tool Encapsulation**: Agents operate via standard interfaces (`read_state`, `update_state`, `rollback`), fully decoupled.
*   **Write Lock**: Prevents conflict when Writer and Editor compete for state updates.
*   **Snapshot Rollback**: Auto-backup state after each chapter. If logic collapses at Chapter N, rollback to `Snapshot_N-1` instantly.
*   **Causality Graph**: Tracks "Foreshadowing" vs "Payoff". E.g., `H01 (Jade Pendant) -> Impact (Ch50 Ancient Array)`.

### **3. Hybrid Model Routing (Cost & Quality)**
*   Defined dynamically in `config.yaml`:
    *   **Writing (Daily)**: `Qwen-Plus` (Fast, Low Cost).
    *   **Writing (Climax)**: `Claude-3.5-Sonnet` (Strong Logic, High Quality).
    *   **Critic (Review)**: `DeepSeek-R1` (Strong Reasoning).

### **4. Quality Control (QC)**
*   **Character Voice Sandbox**: Maintains `voice_profiles.yaml` to enforce speaking styles (catchphrases, sentence length), preventing homogenization.
*   **Tension Heatmap**: Navigator monitors `Tension_Level`. If 3 consecutive chapters score low, forces "High Conflict Task" in the next chapter.
*   **Anti-AI Flavor Strategy**:
    *   **Sensory Check**: Mandatory non-visual descriptions (Hearing/Smell/Touch) per chapter.
    *   **Dynamic Forbidden List**: Auto-stats and bans AI buzzwords (e.g., "Unbelievable", "As if").

---

## 🚀 4. Execution Plan

1.  **Phase 0 (MVP)**: Build `Engine` core structure, implement StateDB (MCP version) and Controller base logic.
2.  **Phase 1**: Run Writer -> Editor feedback loop, initialize first project.
3.  **Phase 2**: Introduce RedTeam and MemoryBank (RAG) for long-context logic.

**Architecture locked. Ready for code implementation.**
