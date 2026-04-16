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


def test_extract_empty_text():
    profile = StyleExtractor.extract("")
    assert profile.avg_sentence_length == 0
    assert profile.vocabulary_richness == 0
    assert profile.tone == "casual"


def test_extract_long_text():
    text = "。".join(["他走了进来"] * 100) + "。"
    profile = StyleExtractor.extract(text)
    assert profile.avg_sentence_length > 0
    assert profile.vocabulary_richness < 1.0  # repeated text


def test_style_profile_consistency():
    same_text = "他仿佛看到了未来。然而，尽管困难重重，他依然坚持。"
    p1 = StyleExtractor.extract(same_text)
    p2 = StyleExtractor.extract(same_text)
    assert p1.avg_sentence_length == p2.avg_sentence_length
    assert p1.tone == p2.tone


def test_style_extractor_integration_via_api(tmp_path):
    """Integration test: verify style extraction works via API endpoint."""
    from fastapi.testclient import TestClient
    from Studio.api import create_app

    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client:
        response = client.post("/api/style/extract", json={
            "text": "他走进了房间，仿佛回到了过去。",
        })
        assert response.status_code == 200
        data = response.json()
        assert "avg_sentence_length" in data
        assert "tone" in data


def test_style_fingerprint_via_api(tmp_path):
    """Integration test: verify fingerprint generation via API endpoint."""
    from fastapi.testclient import TestClient
    from Studio.api import create_app

    app = create_app(
        seed_data=False,
        db_path=":memory:",
        projects_dir=str(tmp_path / "projects"),
    )
    with TestClient(app) as client:
        response = client.post("/api/style/fingerprint", json={
            "text": "他走进了房间。「你好」他问道。",
        })
        assert response.status_code == 200
        data = response.json()
        assert "fingerprint" in data
        assert "style_profile" in data
        assert "tone" in data["style_profile"]
