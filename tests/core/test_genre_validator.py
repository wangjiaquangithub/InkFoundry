"""Tests for Genre Validator."""
from __future__ import annotations

from Engine.core.genre_validator import GenreValidator, GENRE_CONFIGS


def test_validate_valid_xuanhuan_chapter():
    content = "修炼者们都在讨论新发现的功法，境界突破后的感觉真好。" * 200
    issues = GenreValidator.validate_chapter("xuanhuan", content)
    assert len(issues) == 0


def test_validate_short_chapter():
    issues = GenreValidator.validate_chapter("xuanhuan", "太短了")
    assert any("太短" in i for i in issues)


def test_validate_long_chapter():
    content = "x" * 10000
    issues = GenreValidator.validate_chapter("romance", content)
    assert any("太长" in i for i in issues)


def test_validate_missing_required_element():
    content = "这是一个普通的故事，没有修炼没有境界。"
    issues = GenreValidator.validate_chapter("xuanhuan", content)
    assert any("缺少" in i for i in issues)


def test_validate_forbidden_element():
    content = "他拿起了智能手机，打开微信。修炼者在微信上交流功法。"
    issues = GenreValidator.validate_chapter("xuanhuan", content)
    assert any("禁用" in i for i in issues)


def test_validate_unknown_genre():
    issues = GenreValidator.validate_chapter("cooking", "内容")
    assert any("Unknown" in i for i in issues)


def test_list_genres():
    genres = GenreValidator.list_genres()
    assert len(genres) == 5
    assert "xuanhuan" in genres
    assert "xianxia" in genres


def test_get_genre_info():
    rule = GenreValidator.get_genre_info("wuxia")
    assert rule is not None
    assert "武功" in rule.required_elements
