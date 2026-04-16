# Plan: Configurable Model API Key Support

## Context

`.env` already defines LLM configuration (`LLM_API_KEY`, `LLM_BASE_URL`, `DEFAULT_MODEL`, per-role model overrides), but no code reads these values. Agents receive `model_name` as a string with no actual API integration.

## Goal

Add `Engine/config.py` to load `.env` variables, thread them through `ModelRouter` and `BaseAgent`, enabling configurable per-role API keys and endpoints.

## Tasks

### Task 1: Create `Engine/config.py` — Environment Config Loader

**File**: `Engine/config.py` (new)

```python
"""Load and validate LLM configuration from environment variables."""
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

    def to_router_config(self) -> dict:
        return {
            "default_model": self.llm.default_model,
            "api_key": self.llm.api_key,
            "base_url": self.llm.base_url,
            **self.role_models,
        }
```

### Task 2: Extend `Engine/utils/router.py` — Return API Credentials

**File**: `Engine/utils/router.py` (modify)

- Add `api_key` and `base_url` to `__init__`
- `get_model()` returns `dict` with `model`, `api_key`, `base_url`

### Task 3: Extend `Engine/agents/base.py` — Hold LLM Client Config

**File**: `Engine/agents/base.py` (modify)

- Add `api_key` and `base_url` to `__init__`
- Add `_build_client()` method returning OpenAI-compatible SDK client

### Task 4: Tests

**Files**:
- `tests/core/test_config.py` (new) — test env loading, defaults, ValueError on missing key
- `tests/utils/test_router.py` (modify) — test router returns api_key/base_url
- `tests/agents/test_base_agent.py` (modify) — test client building

## Files Changed

| File | Action |
|---|---|
| `Engine/config.py` | **new** |
| `Engine/utils/router.py` | modify |
| `Engine/agents/base.py` | modify |
| `tests/core/test_config.py` | **new** |
| `tests/utils/test_router.py` | modify |
| `tests/agents/test_base_agent.py` | modify |

## Risk

- `.env` contains a real API key — should be moved to `.env.example` with placeholder
- No LLM call integration yet — this plan only wires config, actual API calls are a future task
