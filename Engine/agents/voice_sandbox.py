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
        return f"""{system_prompt}
### Voice Constraints
- Style: {self.config.get('style', 'default')}
- Tone: {self.config.get('tone', 'neutral')}
- Pacing: {self.config.get('pacing', 'moderate')}
"""
