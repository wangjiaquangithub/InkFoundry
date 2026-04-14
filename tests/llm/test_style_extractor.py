"""Tests for Style Extractor."""
from __future__ import annotations

from Engine.llm.style_extractor import StyleExtractor


def test_extract_basic():
    text = "张三走进房间。李四坐在那里。他们相视一笑。"
    profile = StyleExtractor.extract(text)
    assert profile.avg_sentence_length > 0
    assert profile.vocabulary_richness > 0


def test_extract_tone_poetic():
    text = "他仿佛看到了希望。那光芒宛如晨曦，照亮了黑暗。"
    profile = StyleExtractor.extract(text)
    assert profile.tone == "poetic"


def test_extract_tone_formal():
    text = "然而，尽管如此，倘若不是如此，因此我们必须慎重考虑。"
    profile = StyleExtractor.extract(text)
    assert profile.tone == "formal"


def test_detect_patterns():
    text = "他走进了房间。「你好吗？」他问道。"
    patterns = StyleExtractor._detect_patterns(text)
    assert "第三人称叙述" in patterns
    assert "对话驱动" in patterns


def test_generate_prompt():
    profile = StyleExtractor.extract("测试文本。另一个句子。")
    prompt = StyleExtractor.generate_prompt(profile, "武侠故事")
    assert "武侠故事" in prompt
    assert "平均句长" in prompt
