"""Style extraction and cloning from existing text."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class StyleProfile:
    avg_sentence_length: float
    avg_paragraph_length: float  # in sentences
    vocabulary_richness: float  # unique words / total words
    common_patterns: list[str]
    tone: str  # "formal", "casual", "poetic", "direct"


class StyleExtractor:
    """Analyzes text and extracts stylistic features."""

    @staticmethod
    def extract(text: str) -> StyleProfile:
        """Extract style features from the given text.

        Args:
            text: The text to analyze.

        Returns:
            A StyleProfile with extracted features.
        """
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        words = list(text)
        unique_words = set(words)

        avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
        # avg sentences per paragraph
        avg_para_len = sum(max(1, len([s for s in re.split(r'[。！？]', p) if s.strip()])) for p in paragraphs) / max(len(paragraphs), 1)
        vocab_richness = len(unique_words) / max(len(words), 1)

        patterns = StyleExtractor._detect_patterns(text)
        tone = StyleExtractor._detect_tone(text)

        return StyleProfile(
            avg_sentence_length=avg_sentence_len,
            avg_paragraph_length=avg_para_len,
            vocabulary_richness=vocab_richness,
            common_patterns=patterns,
            tone=tone,
        )

    @staticmethod
    def _detect_patterns(text: str) -> list[str]:
        """Detect narrative patterns in the text."""
        patterns = []
        if re.search(r'他[走了进去来到了坐在]', text):
            patterns.append("第三人称叙述")
        if re.search(r'[「"]', text):
            patterns.append("对话驱动")
        if re.search(r'[仿佛似乎不禁]', text):
            patterns.append("修饰语丰富")
        if re.search(r'[。]{2,}', text):
            patterns.append("省略号使用")
        return patterns

    @staticmethod
    def _detect_tone(text: str) -> str:
        """Detect the overall tone of the text."""
        formal_words = ["因此", "然而", "尽管", "既然", "倘若"]
        poetic_words = ["仿佛", "似乎", "宛如", "犹如", "宛若"]

        formal_count = sum(1 for w in formal_words if w in text)
        poetic_count = sum(1 for w in poetic_words if w in text)

        if poetic_count > formal_count:
            return "poetic"
        elif formal_count > poetic_count:
            return "formal"
        return "casual"

    @staticmethod
    def generate_prompt(style: StyleProfile, topic: str) -> str:
        """Generate a writing prompt that matches the extracted style.

        Args:
            style: The StyleProfile to match.
            topic: The topic to write about.

        Returns:
            A formatted prompt string.
        """
        return (
            f"请按照以下风格写作：\n"
            f"- 平均句长: {style.avg_sentence_length:.1f} 字\n"
            f"- 段落平均句子数: {style.avg_paragraph_length:.1f}\n"
            f"- 词汇丰富度: {style.vocabulary_richness:.2f}\n"
            f"- 风格特征: {', '.join(style.common_patterns)}\n"
            f"- 语调: {style.tone}\n\n"
            f"主题: {topic}"
        )
