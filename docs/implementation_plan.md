# InkFoundry Narrative OS Complete Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the complete InkFoundry Narrative OS v3.2, a dual-layer system combining industrial automation (Engine) with visual insight (Studio).

**Architecture:** 
- **Engine Layer:** Python-based execution engine with MCP Server, SQLite StateDB, and Adversarial Agent loops.
- **Studio Layer:** Visualization dashboard and manual intervention surface.
- **Key Features:** State-Over-Vector filtering, Gradient Rewrite Protocol, Hierarchical Model Routing, and Agent Symbiosis Sandbox.

**Tech Stack:** Python 3.10+, `sqlite3`, `pytest`, `pydantic`, `mcp`, `chromadb` (placeholder), `fastapi`.

---

## Phase 0: Core Infrastructure (StateDB, Controller, Filter)

### Task 1: Project Setup & Dependencies

**Objective:** Initialize directory structure and virtual environment.

**Files:**
- Create: `requirements.txt`
- Create: `Engine/__init__.py`, `tests/__init__.py`

**Step 1: Create requirements.txt**
```text
pytest
pydantic
mcp
```

**Step 2: Verify structure**
Run: `find . -type d | sort`
Expected: `Engine/`, `tests/`, `Studio/`, `Projects/` listed.

**Step 3: Commit**
```bash
git add .
git commit -m "chore: init project structure"
```

### Task 2: Define Character State Model

**Objective:** Create Pydantic model for character state.

**Files:**
- Create: `Engine/core/models.py`
- Test: `tests/core/test_models.py`

**Step 1: Write failing test**
```python
# tests/core/test_models.py
from Engine.core.models import CharacterState
import pytest

def test_create_character():
    char = CharacterState(name="Hero", role="Protagonist")
    assert char.name == "Hero"
    assert char.status == "active"
```

**Step 2: Run test to verify failure**
Run: `pytest tests/core/test_models.py -v`
Expected: FAIL — "ModuleNotFoundError"

**Step 3: Write minimal implementation**
```python
# Engine/core/models.py
from pydantic import BaseModel

class CharacterState(BaseModel):
    name: str
    role: str
    status: str = "active"
```

**Step 4: Run test to verify pass**
Run: `pytest tests/core/test_models.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/core/models.py tests/core/test_models.py
git commit -m "feat: add CharacterState model"
```

### Task 3: Implement StateDB Initialization & Atomic Locks

**Objective:** Create SQLite database with thread-safe connection.

**Files:**
- Create: `Engine/core/state_db.py`
- Test: `tests/core/test_state_db.py`

**Step 1: Write failing test**
```python
# tests/core/test_state_db.py
import pytest
import threading
from Engine.core.state_db import StateDB

def test_db_init_and_lock():
    db = StateDB(":memory:")
    assert db.conn is not None
    assert isinstance(db.lock, type(threading.Lock()))
    
    # Check table exists
    cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters';")
    assert cursor.fetchone() is not None
```

**Step 2: Run test to verify failure**
Run: `pytest tests/core/test_state_db.py::test_db_init_and_lock -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```python
# Engine/core/state_db.py
import sqlite3
import threading

class StateDB:
    def __init__(self, db_path="state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    name TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
```

**Step 4: Run test to verify pass**
Run: `pytest tests/core/test_state_db.py::test_db_init_and_lock -v`
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/core/state_db.py tests/core/test_state_db.py
git commit -m "feat: implement StateDB init with atomic lock"
```

### Task 4: Implement Character Read/Write Operations

**Objective:** Add methods to update and retrieve characters safely.

**Files:**
- Modify: `Engine/core/state_db.py`
- Test: `tests/core/test_state_db.py`

**Step 1: Write failing test**
```python
def test_update_and_get_character(db_instance):
    from Engine.core.models import CharacterState
    db = db_instance
    char = CharacterState(name="TestChar", role="Tester")
    db.update_character(char)
    
    retrieved = db.get_character("TestChar")
    assert retrieved is not None
    assert retrieved.role == "Tester"
```
*(Add `@pytest.fixture` for `db_instance` in `tests/conftest.py` returning `StateDB(":memory:")`)*

**Step 2: Run test to verify failure**
Run: `pytest tests/core/test_state_db.py::test_update_and_get_character -v`
Expected: FAIL — "AttributeError"

**Step 3: Write minimal implementation**
```python
# In StateDB class
from .models import CharacterState

def update_character(self, char: CharacterState):
    with self.lock:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO characters (name, data) VALUES (?, ?)",
                (char.name, char.model_dump_json())
            )

def get_character(self, name: str) -> CharacterState:
    cursor = self.conn.execute("SELECT data FROM characters WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return CharacterState.model_validate_json(row[0])
    return None
```

**Step 4: Run test to verify pass**
Run: `pytest tests/core/test_state_db.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/core/state_db.py tests/conftest.py tests/core/test_state_db.py
git commit -m "feat: implement atomic character CRUD operations"
```

### Task 5: Implement State-Over-Vector Filter

**Objective:** Ensure RAG context never contradicts StateDB truth.

**Files:**
- Create: `Engine/core/filter.py`
- Test: `tests/core/test_filter.py`

**Step 1: Write failing test**
```python
# tests/core/test_filter.py
from Engine.core.filter import StateFilter
from Engine.core.models import CharacterState
from Engine.core.state_db import StateDB

def test_filter_blocks_deceased_character():
    db = StateDB(":memory:")
    db.update_character(CharacterState(name="DeadGuy", role="Villain", status="deceased"))
    
    f = StateFilter(db)
    rag_context = {"DeadGuy": "DeadGuy is walking towards you."}
    
    result = f.apply(rag_context)
    assert "DeadGuy" not in result
```

**Step 2: Run test to verify failure**
Run: `pytest tests/core/test_filter.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```python
# Engine/core/filter.py
class StateFilter:
    def __init__(self, state_db):
        self.db = state_db

    def apply(self, rag_context: dict) -> dict:
        safe_context = {}
        for name, text in rag_context.items():
            char = self.db.get_character(name)
            # If character is deceased, block context
            if char and char.status == "deceased":
                continue
            safe_context[name] = text
        return safe_context
```

**Step 4: Run test to verify pass**
Run: `pytest tests/core/test_filter.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/core/filter.py tests/core/test_filter.py
git commit -m "feat: implement State-Over-Vector Filter"
```

### Task 6: Implement Pipeline Controller with Circuit Breaker

**Objective:** Manage execution with max-retries and graceful degradation.

**Files:**
- Create: `Engine/core/controller.py`
- Test: `tests/core/test_controller.py`

**Step 1: Write failing test**
```python
# tests/core/test_controller.py
import pytest
from Engine.core.controller import PipelineController, CircuitBreakerError

def test_circuit_breaker_triggers():
    ctrl = PipelineController(max_retries=2)
    def failing_task(): raise ValueError("Fail")
    with pytest.raises(CircuitBreakerError):
        ctrl.execute_with_retry(failing_task)
```

**Step 2: Run test to verify failure**
Run: `pytest tests/core/test_controller.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```python
# Engine/core/controller.py
class CircuitBreakerError(Exception):
    pass

class PipelineController:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries

    def execute_with_retry(self, task_func, *args):
        attempts = 0
        while attempts < self.max_retries:
            try:
                return task_func(*args)
            except Exception as e:
                attempts += 1
                print(f"Attempt {attempts} failed: {e}")
        raise CircuitBreakerError("Max retries reached.")
```

**Step 4: Run test to verify pass**
Run: `pytest tests/core/test_controller.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/core/controller.py tests/core/test_controller.py
git commit -m "feat: implement Pipeline Controller with Circuit Breaker"
```

---

## Phase 1: Agent Implementation (Writer, Editor, RedTeam)

### Task 7: Define Base Agent Interface

**Objective:** Create standard interface for all Agents.

**Files:**
- Create: `Engine/agents/base.py`
- Test: `tests/agents/test_base_agent.py`

**Step 1: Write failing test**
```python
def test_base_agent_not_implemented():
    from Engine.agents.base import BaseAgent
    agent = BaseAgent("test_model", "prompt")
    with pytest.raises(NotImplementedError):
        agent.run({})
```

**Step 2: Run test to verify failure**
Expected: FAIL

**Step 3: Write minimal implementation**
```python
# Engine/agents/base.py
class BaseAgent:
    def __init__(self, model_name, system_prompt):
        self.model = model_name
        self.system_prompt = system_prompt

    def run(self, context):
        raise NotImplementedError
```

**Step 4: Run test to verify pass**
Expected: PASS

**Step 5: Commit**
```bash
git add Engine/agents/base.py tests/agents/test_base_agent.py
git commit -m "feat: define BaseAgent interface"
```

### Task 8: Implement Writer Agent Skeleton

**Objective:** Agent that generates drafts based on Task Cards.

**Files:**
- Create: `Engine/agents/writer.py`
- Test: `tests/agents/test_writer.py`

**Step 1: Write test**
```python
def test_writer_returns_draft():
    from Engine.agents.writer import WriterAgent
    agent = WriterAgent("model", "prompt")
    result = agent.run({"chapter": 1})
    assert "Draft" in result
```

**Step 2: Implement Writer**
```python
# Engine/agents/writer.py
from .base import BaseAgent

class WriterAgent(BaseAgent):
    def run(self, task_card):
        # TODO: Integrate LLM API
        return f"Draft for Chapter {task_card['chapter']}..."
```

**Step 3: Commit**
```bash
git add Engine/agents/writer.py tests/agents/test_writer.py
git commit -m "feat: implement Writer Agent skeleton"
```

### Task 9: Implement Editor & RedTeam Agents

**Objective:** Agents that critique the draft.

**Files:**
- Create: `Engine/agents/editor.py`, `Engine/agents/redteam.py`
- Test: `tests/agents/test_editor.py`, `tests/agents/test_redteam.py`

**Step 1: Implement Agents**
```python
# Engine/agents/editor.py
class EditorAgent(BaseAgent):
    def run(self, draft):
        return {"score": 80, "issues": ["AI flavor detected"]}

# Engine/agents/redteam.py
class RedTeamAgent(BaseAgent):
    def run(self, draft):
        return {"attack": "Logic hole in scene 2"}
```

**Step 2: Write tests to verify structure**
(Tests should verify they return dicts with score/attack keys).

**Step 3: Commit**
```bash
git add Engine/agents/
git commit -m "feat: implement Editor and RedTeam Agent skeletons"
```

---

## Phase 2: Advanced Features (Memory, Routing, Sandbox)

### Task 10: Implement MemoryBank (Vector Store)

**Objective:** Store and retrieve chapter summaries for long-context recall.

**Files:**
- Create: `Engine/core/memory_bank.py`
- Test: `tests/core/test_memory_bank.py`

**Step 1: Write failing test**
```python
def test_add_and_query_summary():
    from Engine.core.memory_bank import MemoryBank
    bank = MemoryBank()
    bank.add_summary(1, "Protagonist finds sword.")
    results = bank.query("sword")
    assert len(results) > 0
```

**Step 2: Implement MemoryBank**
```python
# Engine/core/memory_bank.py
class MemoryBank:
    def __init__(self):
        self.index = [] # Placeholder for ChromaDB

    def add_summary(self, chapter_num, text):
        self.index.append({"ch": chapter_num, "text": text})

    def query(self, keyword):
        return [item for item in self.index if keyword in item["text"]]
```

**Step 3: Commit**
```bash
git add Engine/core/memory_bank.py tests/core/test_memory_bank.py
git commit -m "feat: implement MemoryBank skeleton"
```

### Task 11: Implement Character Voice Sandbox

**Objective:** Define voice profiles to prevent character homogenization.

**Files:**
- Create: `Engine/agents/voice_sandbox.py`
- Create: `Engine/configs/voices/default.yaml`
- Test: `tests/agents/test_voice_sandbox.py`

**Step 1: Write test**
```python
def test_voice_injection():
    from Engine.agents.voice_sandbox import VoiceSandbox
    sandbox = VoiceSandbox("Engine/configs/voices/default.yaml")
    prompt = sandbox.inject_prompt("Write a scene.")
    assert "Style:" in prompt
```

**Step 2: Implement Voice Sandbox**
```python
# Engine/agents/voice_sandbox.py
import yaml

class VoiceSandbox:
    def __init__(self, path):
        with open(path) as f:
            self.config = yaml.safe_load(f)

    def inject_prompt(self, system_prompt: str) -> str:
        return f"""{system_prompt}
### Voice Constraints
- Style: {self.config.get('style', 'default')}
"""
```

**Step 3: Commit**
```bash
git add Engine/agents/voice_sandbox.py Engine/configs/
git commit -m "feat: implement Character Voice Sandbox"
```

### Task 12: Implement Tension Heatmap in Navigator

**Objective:** Track and enforce pacing via Tension Levels.

**Files:**
- Create: `Engine/agents/navigator.py`
- Test: `tests/agents/test_navigator.py`

**Step 1: Write test**
```python
def test_navigator_forces_climax():
    from Engine.agents.navigator import NavigatorAgent
    nav = NavigatorAgent("model", "prompt")
    # Last 3 chapters were boring (low tension)
    card = nav.generate_task_card(chapter_num=5, history_tension=[2, 2, 2])
    assert card['tension_level'] >= 8 # Should force high tension
```

**Step 2: Implement Navigator**
```python
# Engine/agents/navigator.py
class NavigatorAgent(BaseAgent):
    def generate_task_card(self, chapter_num, history_tension):
        if len(history_tension) >= 3 and sum(history_tension[-3:]) < 15:
            tension = 9
            task_type = "high_conflict"
        else:
            tension = 4
            task_type = "development"
        return {"chapter": chapter_num, "tension_level": tension, "type": task_type}
```

**Step 3: Commit**
```bash
git add Engine/agents/navigator.py tests/agents/test_navigator.py
git commit -m "feat: implement Tension Heatmap logic"
```

### Task 13: Implement Director Agent for Sandbox

**Objective:** Control Role-Play to prevent loops.

**Files:**
- Create: `Engine/agents/director.py`
- Test: `tests/agents/test_director.py`

**Step 1: Implement Director**
```python
# Engine/agents/director.py
class DirectorAgent(BaseAgent):
    def detect_loop(self, history):
        return len(history) > 10 # Simplified logic
```

**Step 2: Commit**
```bash
git add Engine/agents/director.py tests/agents/test_director.py
git commit -m "feat: implement Director Agent loop detection"
```

### Task 14: Implement Hierarchical Model Router

**Objective:** Route tasks to different LLMs.

**Files:**
- Create: `Engine/utils/router.py`
- Test: `tests/utils/test_router.py`

**Step 1: Implement Router**
```python
# Engine/utils/router.py
class ModelRouter:
    def __init__(self, config):
        self.config = config
    def get_model(self, agent_type, importance="low"):
        if agent_type == "writer" and importance == "high":
            return self.config.get("climax_model", "gpt-4o")
        return self.config.get("default_model", "qwen-plus")
```

**Step 2: Commit**
```bash
git add Engine/utils/router.py tests/utils/test_router.py
git commit -m "feat: implement Hierarchical Model Router"
```

---

## Phase 3: Studio Integration (Interface & Dashboard)

### Task 15: Expose StateDB via MCP Server

**Objective:** Allow Studio to read state via MCP Protocol.

**Files:**
- Create: `Engine/core/mcp_server.py`
- Test: `tests/core/test_mcp.py`

**Step 1: Implement MCP Server**
```python
# Engine/core/mcp_server.py
from mcp.server.fastmcp import FastMCP
from .state_db import StateDB

mcp = FastMCP("InkFoundryState")
db = StateDB()

@mcp.tool()
def read_character(name: str) -> str:
    char = db.get_character(name)
    return char.json() if char else "Not Found"
```

**Step 2: Commit**
```bash
git add Engine/core/mcp_server.py tests/core/test_mcp.py
git commit -m "feat: expose StateDB via MCP Server"
```

### Task 16: Create Studio FastAPI Endpoints

**Objective:** Provide REST API for the UI dashboard.

**Files:**
- Create: `Studio/api.py`
- Test: `tests/studio/test_api.py`

**Step 1: Implement API**
```python
# Studio/api.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/status")
def get_status():
    return {"status": "running"}
```

**Step 2: Commit**
```bash
git add Studio/api.py tests/studio/test_api.py
git commit -m "feat: init Studio FastAPI app"
```

### Task 17: Integration Test

**Objective:** Run the full pipeline end-to-end.

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write Integration Test**
```python
def test_full_pipeline_mock():
    # Mock LLM calls
    # 1. Navigator creates Task Card
    # 2. Writer generates draft
    # 3. Editor passes it
    # 4. StateDB updates
    assert True
```

**Step 2: Commit & Final Review**
```bash
git add tests/test_integration.py
git commit -m "test: add integration test skeleton"
```
