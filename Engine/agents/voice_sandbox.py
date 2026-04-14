"""Voice Sandbox - injects character voice profiles into prompts."""
from __future__ import annotations

import yaml


class VoiceSandbox:
    """Loads voice configuration and injects constraints into prompts.

    Prevents character homogenization by enforcing unique voice profiles.
    """

    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def inject_prompt(self, system_prompt: str) -> str:
        """Inject voice constraints into a system prompt.

        Args:
            system_prompt: The base prompt to enhance.

        Returns:
            Prompt with voice constraints appended.
        """
        parts = [system_prompt]

        style = self.config.get("style", "default")
        tone = self.config.get("tone", "neutral")
        pacing = self.config.get("pacing", "moderate")

        parts.append("角色声音配置:")
        parts.append(f"  风格: {style}")
        parts.append(f"  语调: {tone}")
        parts.append(f"  节奏: {pacing}")

        speech_patterns = self.config.get("speech_patterns", [])
        if speech_patterns:
            parts.append(f"  说话习惯: {', '.join(speech_patterns)}")

        vocabulary = self.config.get("vocabulary_list", [])
        if vocabulary:
            parts.append(f"  专属词汇: {', '.join(vocabulary)}")

        sensory_bias = self.config.get("sensory_bias", {})
        if sensory_bias:
            parts.append(
                f"  感官偏好: {', '.join(f'{k}: {v}' for k, v in sensory_bias.items())}"
            )

        forbidden = self.config.get("forbidden_words", [])
        if forbidden:
            parts.append(f"  禁止使用: {', '.join(forbidden)}")

        return "\n".join(parts)
