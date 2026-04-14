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
