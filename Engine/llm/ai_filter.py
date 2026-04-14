"""AI flavor detector — checks for common AI writing patterns."""
from __future__ import annotations
import re
from dataclasses import dataclass


# Common AI cliches in Chinese writing
AI_CLICHES = [
    "不禁", "仿佛", "似乎", "无疑", "值得注意的是",
    "值得一提的是", "不难发现", "显而易见", "众所周知",
    "令人", "不由得", "渐渐地", "突然之间",
]


@dataclass
class AIFilterIssue:
    type: str  # "repetitive_structure" | "ai_cliche" | "low_sensory" | "over_adjective"
    severity: float  # 0-1
    description: str
    position: tuple[int, int]  # (start, end) character indices


class AIFilter:
    def __init__(self, voice_profile: dict):
        self._voice_profile = voice_profile

    def analyze(self, text: str) -> list[AIFilterIssue]:
        issues = []
        issues.extend(self._check_cliches(text))
        issues.extend(self._check_repetitive_structure(text))
        return issues

    def score(self, text: str) -> float:
        """Return 0-100 de-AI score. 100 = no AI flavor, 0 = heavily AI."""
        issues = self.analyze(text)
        penalty = sum(i.severity * 20 for i in issues)
        return max(0, min(100, 100 - penalty))

    def _check_cliches(self, text: str) -> list[AIFilterIssue]:
        issues = []
        for cliche in AI_CLICHES:
            pos = 0
            while True:
                idx = text.find(cliche, pos)
                if idx == -1:
                    break
                issues.append(AIFilterIssue(
                    type="ai_cliche",
                    severity=0.5,
                    description=f"AI 套话: '{cliche}'",
                    position=(idx, idx + len(cliche)),
                ))
                pos = idx + len(cliche)
        return issues

    def _check_repetitive_structure(self, text: str) -> list[AIFilterIssue]:
        issues = []
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return issues

        for i in range(len(sentences) - 2):
            first_words = []
            for j in range(3):
                s = sentences[i + j]
                first_words.append(s[:2] if len(s) >= 2 else s)
            if first_words[0] == first_words[1] == first_words[2]:
                issues.append(AIFilterIssue(
                    type="repetitive_structure",
                    severity=0.7,
                    description=f"连续3句相同开头: '{first_words[0]}'",
                    position=(0, 0),
                ))
        return issues
