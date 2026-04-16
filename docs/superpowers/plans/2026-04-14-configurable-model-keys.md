# Configurable Model API Keys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `.env` LLM configuration (`LLM_API_KEY`, `LLM_BASE_URL`, per-role model overrides) through `EngineConfig` -> `ModelRouter` -> `BaseAgent`, enabling configurable per-role API keys and endpoints.

**Architecture:** Create `Engine/config.py` as the single source of config, loaded via `os.getenv`. Extend `ModelRouter` to return `(model_name, api_key, base_url)` tuples. Extend `BaseAgent` to accept and hold these credentials, with a `_build_client()` helper for future LLM API integration. TDD throughout.

**Tech Stack:** Python 3.10+, `os.getenv`, `pytest` monkeypatch, dataclasses

---

### Task 1: Create `Engine/config.py` — Environment Config Loader

**Files:**
- Create: `Engine/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_config.py
import pytest
from Engine.config import EngineConfig


def test_config_from_env(monkeypatch):
    """Test loading all config values from environment variables."""
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")
    monkeypatch.setenv("EDITOR_MODEL", "claude-sonnet")
    monkeypatch.setenv("REDTEAM_MODEL", "gpt-4o")
    monkeypatch.setenv("NAVIGATOR_MODEL", "qwen-turbo")

    cfg = EngineConfig.from_env()

    assert cfg.llm.api_key == "test-key-123"
    assert cfg.llm.base_url == "https://example.com/v1"
    assert cfg.llm.default_model == "qwen-turbo"
    assert cfg.role_models["writer"] == "qwen-plus"
    assert cfg.role_models["editor"] == "claude-sonnet"
    assert cfg.role_models["redteam"] == "gpt-4o"
    assert cfg.role_models["navigator"] == "qwen-turbo"


def test_config_missing_api_key(monkeypatch):
    """Test that missing LLM_API_KEY raises ValueError."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(ValueError, match="LLM_API_KEY"):
        EngineConfig.from_env()


def test_config_defaults(monkeypatch):
    """Test default values when only LLM_API_KEY is set."""
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)

    cfg = EngineConfig.from_env()

    assert cfg.llm.base_url == "https://api.openai.com/v1"
    assert cfg.llm.default_model == "qwen-plus"
    # All role models should default to default_model
    for role in ("writer", "editor", "redteam", "navigator", "director"):
        assert cfg.role_models[role] == "qwen-plus"


def test_to_router_config(monkeypatch):
    """Test router config generation."""
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")

    cfg = EngineConfig.from_env()
    rc = cfg.to_router_config()

    assert rc["api_key"] == "key"
    assert rc["base_url"] == "https://example.com/v1"
    assert rc["default_model"] == "qwen-turbo"
    assert rc["writer"] == "qwen-plus"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_config.py -v`
Expected: FAIL — "ModuleNotFoundError: No module named 'Engine.config'"

- [ ] **Step 3: Write minimal implementation**

```python
# Engine/config.py
"""Load LLM configuration from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "qwen-plus"


@dataclass
class EngineConfig:
    """Full engine configuration loaded from environment."""
    llm: LLMConfig
    role_models: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "EngineConfig":
        api_key = os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable is required")

        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        default_model = os.getenv("DEFAULT_MODEL", "qwen-plus")

        llm = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
        )

        role_models = {}
        for role in ("writer", "editor", "redteam", "navigator", "director"):
            env_key = f"{role.upper()}_MODEL"
            role_models[role] = os.getenv(env_key, default_model)

        return cls(llm=llm, role_models=role_models)

    def to_router_config(self) -> dict[str, str]:
        """Convert to ModelRouter-compatible config dict."""
        return {
            "default_model": self.llm.default_model,
            "api_key": self.llm.api_key,
            "base_url": self.llm.base_url,
            **self.role_models,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/config.py tests/core/test_config.py
git commit -m "feat: add EngineConfig for LLM environment variable loading"
```

---

### Task 2: Extend `Engine/utils/router.py` — Return API Credentials

**Files:**
- Modify: `Engine/utils/router.py`
- Test: `tests/utils/test_router.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/utils/test_router.py`:

```python
def test_router_returns_credentials():
    """Test that get_model returns dict with api_key and base_url."""
    config = {
        "default_model": "qwen-plus",
        "api_key": "secret-key",
        "base_url": "https://api.example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("editor")

    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "secret-key"
    assert result["base_url"] == "https://api.example.com/v1"


def test_router_writer_high_importance_with_credentials():
    """Test writer gets climax model when importance is high."""
    config = {
        "default_model": "qwen-plus",
        "writer": "qwen-max",
        "api_key": "key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("writer", importance="high")

    # Writer with high importance should use role-specific model if available
    assert result["model"] == "qwen-max"
    assert result["api_key"] == "key"
    assert result["base_url"] == "https://example.com/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_router.py -v`
Expected: FAIL — new tests fail because `get_model` returns `str`, not `dict`

- [ ] **Step 3: Write minimal implementation**

Replace `Engine/utils/router.py` with:

```python
"""Hierarchical Model Router - routes tasks to different LLMs."""
from __future__ import annotations

from typing import Any, Dict, TypedDict


class ModelInfo(TypedDict):
    """Resolved model configuration."""
    model: str
    api_key: str
    base_url: str


class ModelRouter:
    """Routes tasks to appropriate LLMs based on agent type and importance.

    Hierarchy:
    - L1: Global default model
    - L2: Agent-specific overrides (writer, editor, redteam, navigator, director)
    - L3: Task-level overrides (e.g., climax chapters use higher-tier model)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_model(
        self, agent_type: str, importance: str = "low"
    ) -> ModelInfo:
        """Determine the model to use for a task.

        Args:
            agent_type: The type of agent (writer, editor, etc.).
            importance: Task importance level ('low', 'high').

        Returns:
            ModelInfo dict with model name, api_key, and base_url.
        """
        # Determine model name
        if agent_type == "writer" and importance == "high":
            # L3: Writer with high importance gets role-specific model
            model_name = self.config.get("writer", self.config.get("default_model", "qwen-plus"))
        elif agent_type in self.config:
            # L2: Agent-specific override
            model_name = self.config[agent_type]
        else:
            # L1: Global default
            model_name = self.config.get("default_model", "qwen-plus")

        return ModelInfo(
            model=model_name,
            api_key=self.config.get("api_key", ""),
            base_url=self.config.get("base_url", "https://api.openai.com/v1"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_router.py -v`
Expected: All 6 tests PASS (4 existing + 2 new)

- [ ] **Step 5: Update existing tests that expect str return**

The 4 existing tests in `test_router.py` compare `router.get_model(...)` directly to a string. Update them:

```python
"""Tests for Hierarchical Model Router."""
from Engine.utils.router import ModelRouter


def test_router_default_model():
    config = {"default_model": "qwen-plus"}
    router = ModelRouter(config)
    assert router.get_model("writer")["model"] == "qwen-plus"


def test_router_writer_high_importance():
    config = {
        "default_model": "qwen-plus",
        "writer": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="high")["model"] == "claude-opus"


def test_router_writer_low_importance():
    config = {
        "default_model": "qwen-plus",
        "writer": "claude-opus",
    }
    router = ModelRouter(config)
    assert router.get_model("writer", importance="low")["model"] == "qwen-plus"


def test_router_editor_always_default():
    config = {
        "default_model": "qwen-plus",
        "editor": "claude-sonnet",
    }
    router = ModelRouter(config)
    assert router.get_model("editor", importance="high")["model"] == "claude-sonnet"


def test_router_returns_credentials():
    """Test that get_model returns dict with api_key and base_url."""
    config = {
        "default_model": "qwen-plus",
        "api_key": "secret-key",
        "base_url": "https://api.example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("editor")

    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "secret-key"
    assert result["base_url"] == "https://api.example.com/v1"


def test_router_writer_high_importance_with_credentials():
    """Test writer gets role-specific model when importance is high."""
    config = {
        "default_model": "qwen-plus",
        "writer": "qwen-max",
        "api_key": "key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)
    result = router.get_model("writer", importance="high")

    assert result["model"] == "qwen-max"
    assert result["api_key"] == "key"
    assert result["base_url"] == "https://example.com/v1"
```

- [ ] **Step 6: Run full test suite to verify no regressions**

Run: `pytest -v`
Expected: All tests PASS (including existing 63)

- [ ] **Step 7: Commit**

```bash
git add Engine/utils/router.py tests/utils/test_router.py
git commit -m "feat: extend ModelRouter to return ModelInfo with api_key and base_url"
```

---

### Task 3: Extend `Engine/agents/base.py` — Hold LLM Client Config

**Files:**
- Modify: `Engine/agents/base.py`
- Test: `tests/agents/test_base_agent.py`

- [ ] **Step 1: Write the failing test**

Replace `tests/agents/test_base_agent.py`:

```python
"""Tests for BaseAgent interface."""
import pytest
from Engine.agents.base import BaseAgent


def test_base_agent_init():
    agent = BaseAgent("test_model", "test prompt")
    assert agent.model == "test_model"
    assert agent.system_prompt == "test prompt"
    assert agent.api_key == ""
    assert agent.base_url == "https://api.openai.com/v1"


def test_base_agent_init_with_credentials():
    agent = BaseAgent(
        "test_model",
        "test prompt",
        api_key="secret-key",
        base_url="https://example.com/v1",
    )
    assert agent.api_key == "secret-key"
    assert agent.base_url == "https://example.com/v1"


def test_base_agent_run_not_implemented():
    agent = BaseAgent("test_model", "test prompt")
    with pytest.raises(NotImplementedError):
        agent.run({})


def test_base_agent_build_client_returns_none_without_openai():
    """Test _build_client returns None when openai package is not available."""
    agent = BaseAgent("test_model", "test prompt", api_key="key")
    # Without openai installed, should return None gracefully
    client = agent._build_client()
    assert client is None


def test_base_agent_from_router_info():
    """Test creating agent from ModelInfo dict."""
    agent = BaseAgent.from_router_info(
        {
            "model": "qwen-plus",
            "api_key": "key",
            "base_url": "https://example.com/v1",
        },
        system_prompt="Write novel.",
    )
    assert agent.model == "qwen-plus"
    assert agent.api_key == "key"
    assert agent.base_url == "https://example.com/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_base_agent.py -v`
Expected: FAIL — `api_key` attribute doesn't exist

- [ ] **Step 3: Write minimal implementation**

Replace `Engine/agents/base.py`:

```python
"""Base agent interface for all narrative agents."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from openai import OpenAI


class BaseAgent:
    """Abstract base class for all agents in the narrative pipeline.

    Subclasses must implement the `run` method.
    """

    def __init__(
        self,
        model_name: str,
        system_prompt: str,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.model = model_name
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.base_url = base_url

    @classmethod
    def from_router_info(
        cls,
        router_info: Dict[str, str],
        system_prompt: str,
    ) -> "BaseAgent":
        """Create an agent from a ModelRouter result.

        Args:
            router_info: Dict with 'model', 'api_key', 'base_url' keys.
            system_prompt: The agent's system prompt.

        Returns:
            A configured agent instance.
        """
        return cls(
            model_name=router_info["model"],
            system_prompt=system_prompt,
            api_key=router_info.get("api_key", ""),
            base_url=router_info.get("base_url", "https://api.openai.com/v1"),
        )

    def run(self, context: Dict[str, Any]) -> Any:
        """Execute the agent's primary task.

        Raises:
            NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")

    def _build_client(self) -> OpenAI | None:
        """Build an OpenAI-compatible client.

        Returns:
            OpenAI client instance, or None if openai package is not installed.
        """
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        except ImportError:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_base_agent.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/agents/base.py tests/agents/test_base_agent.py
git commit -m "feat: extend BaseAgent with api_key, base_url, and from_router_info factory"
```

---

### Task 4: Update Integration Tests + `.env.example`

**Files:**
- Modify: `tests/test_integration.py`
- Create: `.env.example`

- [ ] **Step 1: Update integration tests for new return types**

Replace `tests/test_integration.py`:

```python
"""Integration test - full pipeline end-to-end with mocked LLM calls."""
import pytest
from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState, WorldState, StateSnapshot
from Engine.core.filter import StateFilter
from Engine.core.controller import PipelineController, CircuitBreakerError
from Engine.config import EngineConfig
from Engine.agents.base import BaseAgent
from Engine.agents.writer import WriterAgent
from Engine.agents.editor import EditorAgent
from Engine.agents.redteam import RedTeamAgent
from Engine.agents.navigator import NavigatorAgent
from Engine.agents.director import DirectorAgent
from Engine.core.memory_bank import MemoryBank
from Engine.utils.router import ModelRouter


def test_full_pipeline_mock():
    """End-to-end pipeline test with mocked agents.

    Flow:
    1. Navigator creates Task Card
    2. Writer generates draft
    3. Editor reviews draft
    4. RedTeam attacks draft
    5. StateDB updates character state
    6. MemoryBank stores summary
    7. StateFilter validates context
    """
    # 1. Navigator creates Task Card
    nav = NavigatorAgent("model", "Navigate the plot.")
    task_card = nav.generate_task_card(chapter_num=1, history_tension=[])
    assert task_card["chapter"] == 1
    assert "tension_level" in task_card

    # 2. Writer generates draft
    writer = WriterAgent("model", "Write novel scenes.")
    draft = writer.run(task_card)
    assert "Draft" in draft

    # 3. Editor reviews draft
    editor = EditorAgent("model", "Check logic and style.")
    review = editor.run({"draft": draft})
    assert "score" in review
    assert "issues" in review

    # 4. RedTeam attacks draft
    redteam = RedTeamAgent("model", "Attack the plot.")
    attack = redteam.run({"draft": draft})
    assert "attack" in attack

    # 5. StateDB updates character state
    db = StateDB(":memory:")
    char = CharacterState(name="Hero", role="Protagonist")
    db.update_character(char)
    retrieved = db.get_character("Hero")
    assert retrieved is not None
    assert retrieved.name == "Hero"

    # 6. MemoryBank stores summary
    bank = MemoryBank()
    bank.add_summary(1, "Hero begins the journey.")
    results = bank.query("journey")
    assert len(results) > 0

    # 7. StateFilter validates context (no conflicts)
    sf = StateFilter()
    conflict = sf.check_conflict({"status": "alive"}, {"status": "alive"})
    assert conflict["conflict"] is False


def test_pipeline_with_circuit_breaker():
    """Test that circuit breaker correctly handles persistent failures."""
    db = StateDB(":memory:")
    ctrl = PipelineController(max_retries=2)

    def failing_write():
        raise RuntimeError("Write failed")

    with pytest.raises(CircuitBreakerError):
        ctrl.execute_with_retry(failing_write)

    # StateDB should still be functional after circuit breaker trip
    db.update_character(CharacterState(name="Survivor", role="Support"))
    assert db.get_character("Survivor") is not None


def test_state_filter_blocks_deceased():
    """Test that StateFilter blocks context for deceased characters."""
    db = StateDB(":memory:")
    db.update_character(CharacterState(name="DeadGuy", role="Villain", status="deceased"))
    db.update_character(CharacterState(name="AliveGuy", role="Hero", status="active"))

    f = StateFilter(db)
    rag_context = {
        "DeadGuy": "DeadGuy is walking towards you.",
        "AliveGuy": "AliveGuy stands ready.",
    }
    result = f.apply(rag_context)
    assert "DeadGuy" not in result
    assert "AliveGuy" in result


def test_model_router_integration():
    """Test model router with pipeline configuration."""
    config = {
        "default_model": "qwen-plus",
        "api_key": "test-key",
        "base_url": "https://example.com/v1",
    }
    router = ModelRouter(config)

    result = router.get_model("writer")
    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "test-key"

    result = router.get_model("editor", importance="high")
    assert result["model"] == "qwen-plus"
    assert result["api_key"] == "test-key"


def test_config_router_agent_flow(monkeypatch):
    """Test full flow: EngineConfig -> ModelRouter -> BaseAgent."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEFAULT_MODEL", "qwen-turbo")
    monkeypatch.setenv("WRITER_MODEL", "qwen-plus")

    config = EngineConfig.from_env()
    router = ModelRouter(config.to_router_config())

    info = router.get_model("writer", importance="high")
    assert info["model"] == "qwen-plus"
    assert info["api_key"] == "test-key"

    agent = BaseAgent.from_router_info(info, system_prompt="Write.")
    assert agent.model == "qwen-plus"
    assert agent.api_key == "test-key"
    assert agent.base_url == "https://example.com/v1"
```

- [ ] **Step 2: Run integration tests to verify they pass**

Run: `pytest tests/test_integration.py -v`
Expected: All 5 tests PASS

- [ ] **Step 3: Create `.env.example` with placeholder values**

```text
# InkFoundry Environment Variables
# Copy this file to .env and fill in your actual values.

# LLM Provider Configuration (Aliyun Dashscope / Qwen)
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DEFAULT_MODEL=qwen3.6-plus

# Optional: Model Overrides for Specific Roles
WRITER_MODEL=qwen3.6-plus
EDITOR_MODEL=qwen3.6-plus
REDTEAM_MODEL=qwen3.6-plus
NAVIGATOR_MODEL=qwen3.6-plus
```

- [ ] **Step 4: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add Engine/agents/base.py tests/agents/test_base_agent.py tests/test_integration.py .env.example
git commit -m "feat: integrate config->router->agent flow and add .env.example"
```

---

## Self-Review

### 1. Spec coverage
- `.env` API key loading -> Task 1 (EngineConfig.from_env)
- Per-role model overrides -> Task 1 (role_models dict)
- Router returns credentials -> Task 2 (ModelInfo return type)
- Agent holds credentials -> Task 3 (api_key, base_url params + from_router_info)
- TDD -> Every task has test-first steps
- `.env` security -> Task 4 creates `.env.example` with placeholders

### 2. Placeholder scan
No TBD, TODO, "fill in later", or incomplete code blocks found.

### 3. Type consistency
- `EngineConfig.to_router_config()` returns keys: `default_model`, `api_key`, `base_url`, `writer`, `editor`, `redteam`, `navigator`, `director`
- `ModelRouter.get_model()` returns `ModelInfo` with keys: `model`, `api_key`, `base_url`
- `BaseAgent.from_router_info()` expects dict with keys: `model`, `api_key`, `base_url`
- All consistent across tasks.
