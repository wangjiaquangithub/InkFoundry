"""Prompt builder for LLM calls -- assembles system prompt, context, constraints."""
from __future__ import annotations


class PromptBuilder:
    def __init__(self, system_template: str):
        self._system = system_template
        self._context = ""
        self._constraints: list[str] = []
        self._voice_profile: dict | None = None
        self._state_snapshot: dict | None = None
        self._style_constraint: str | None = None

    def with_context(self, context: str) -> "PromptBuilder":
        self._context = context
        return self

    def with_voice(self, voice_profile: dict) -> "PromptBuilder":
        self._voice_profile = voice_profile
        return self

    def with_state_snapshot(self, snapshot: dict) -> "PromptBuilder":
        self._state_snapshot = snapshot
        return self

    def with_constraints(self, constraints: list[str]) -> "PromptBuilder":
        self._constraints = constraints
        return self

    def with_style(self, style_constraint: str) -> "PromptBuilder":
        self._style_constraint = style_constraint
        return self

    def build(self) -> list[dict]:
        system_parts = [self._system]

        if self._voice_profile:
            vp = self._voice_profile
            if vp.get("speech_patterns"):
                system_parts.append(f"说话风格: {', '.join(vp['speech_patterns'])}")
            if vp.get("forbidden_words"):
                system_parts.append(f"禁止使用的词: {', '.join(vp['forbidden_words'])}")
            if vp.get("sensory_bias"):
                bias = vp["sensory_bias"]
                system_parts.append(f"感官偏好: {', '.join(f'{k}: {v}' for k, v in bias.items())}")

        if self._style_constraint:
            system_parts.append(f"风格约束: {self._style_constraint}")

        user_parts = []
        if self._state_snapshot:
            chars = self._state_snapshot.get("characters", [])
            user_parts.append("当前角色状态:")
            for c in chars:
                user_parts.append(f"  - {c.get('name', '?')}: {c.get('status', '?')}")
            world = self._state_snapshot.get("world", {})
            if world:
                user_parts.append(f"世界状态: {world}")

        if self._context:
            user_parts.append(self._context)

        if self._constraints:
            user_parts.append("写作约束:")
            for c in self._constraints:
                user_parts.append(f"  - {c}")

        user_content = "\n".join(user_parts) if user_parts else ""

        return [
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": user_content},
        ]
