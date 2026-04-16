"""Load LLM configuration from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

DEFAULT_LLM_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
DEFAULT_LLM_MODEL = "qwen3.6-plus"
ROLE_NAMES = ("writer", "editor", "redteam", "navigator", "director")
DASHSCOPE_INCOMPATIBLE_MODEL_PREFIXES = ("claude-", "gpt-", "gemini-")


class InvalidLLMConfigError(ValueError):
    """Raised when model/base URL settings are incompatible."""


def normalize_base_url(base_url: str | None) -> str:
    """Normalize empty base URLs to the project default."""
    value = (base_url or "").strip()
    return value or DEFAULT_LLM_BASE_URL


def normalize_model_name(model_name: str | None) -> str:
    """Normalize empty model names to the project default."""
    value = (model_name or "").strip()
    return value or DEFAULT_LLM_MODEL


def _is_dashscope_base_url(base_url: str) -> bool:
    return "dashscope.aliyuncs.com" in urlparse(base_url).netloc.lower()


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidLLMConfigError("LLM base URL must be a valid http(s) URL")
    return base_url


def validate_model_base_url(model_name: str, base_url: str) -> None:
    """Reject clearly incompatible model/provider combinations."""
    normalized_model = normalize_model_name(model_name)
    normalized_base_url = _validate_base_url(normalize_base_url(base_url))
    lowered_model = normalized_model.lower()

    if _is_dashscope_base_url(normalized_base_url) and lowered_model.startswith(DASHSCOPE_INCOMPATIBLE_MODEL_PREFIXES):
        raise InvalidLLMConfigError(
            f"Model '{normalized_model}' is incompatible with DashScope base URL. "
            "Use a qwen* model or change llm_base_url."
        )


def validate_llm_settings(
    default_model: str,
    base_url: str,
    role_models: dict[str, str] | None = None,
) -> None:
    """Validate the effective LLM settings for default and role-specific models."""
    normalized_base_url = normalize_base_url(base_url)
    validate_model_base_url(default_model, normalized_base_url)

    for model_name in (role_models or {}).values():
        if model_name and model_name.strip():
            validate_model_base_url(model_name, normalized_base_url)


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str
    base_url: str = DEFAULT_LLM_BASE_URL
    default_model: str = DEFAULT_LLM_MODEL


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

        base_url = normalize_base_url(os.getenv("LLM_BASE_URL"))
        default_model = normalize_model_name(os.getenv("DEFAULT_MODEL"))

        llm = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
        )

        role_models = {}
        for role in ROLE_NAMES:
            env_key = f"{role.upper()}_MODEL"
            role_value = os.getenv(env_key, "")
            role_models[role] = normalize_model_name(role_value) if role_value.strip() else default_model

        validate_llm_settings(default_model, base_url, role_models)
        return cls(llm=llm, role_models=role_models)

    def to_router_config(self) -> dict[str, str]:
        """Convert to ModelRouter-compatible config dict."""
        return {
            "default_model": self.llm.default_model,
            "api_key": self.llm.api_key,
            "base_url": self.llm.base_url,
            **self.role_models,
        }
