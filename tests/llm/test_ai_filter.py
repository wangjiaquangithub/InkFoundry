"""Tests for AI Filter."""
from __future__ import annotations

from Engine.llm.ai_filter import AIFilter, AIFilterIssue


def test_ai_filter_detects_cliches():
    f = AIFilter({})
    text = "他不禁感到惊讶，这无疑是最好的结果。"
    issues = f.analyze(text)
    cliche_issues = [i for i in issues if i.type == "ai_cliche"]
    assert len(cliche_issues) >= 2  # "不禁" and "无疑"


def test_ai_filter_score_no_issues():
    f = AIFilter({})
    text = "张三端起茶杯，抿了一口。茶水已经凉了，苦味在舌尖蔓延。"
    score = f.score(text)
    assert 0 <= score <= 100


def test_ai_filter_repetitive_structure():
    f = AIFilter({})
    text = "他慢慢地走着。他慢慢地吃着。他慢慢地想着。"
    issues = f.analyze(text)
    rep_issues = [i for i in issues if i.type == "repetitive_structure"]
    assert len(rep_issues) >= 1


def test_ai_filter_score_range():
    f = AIFilter({})
    score = f.score("测试文本")
    assert 0 <= score <= 100


def test_ai_filter_no_cliches_in_clean_text():
    f = AIFilter({})
    text = "王五推开门，走进书房。桌上放着一封信。"
    issues = f.analyze(text)
    cliche_issues = [i for i in issues if i.type == "ai_cliche"]
    assert len(cliche_issues) == 0


def test_ai_filter_issue_dataclass():
    issue = AIFilterIssue(
        type="ai_cliche",
        severity=0.5,
        description="AI 套话: '不禁'",
        position=(2, 4),
    )
    assert issue.type == "ai_cliche"
    assert issue.severity == 0.5
    assert issue.position == (2, 4)
