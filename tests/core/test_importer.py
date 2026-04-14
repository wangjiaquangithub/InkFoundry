"""Tests for Novel Importer."""
from __future__ import annotations

import os
import tempfile

import pytest

from Engine.core.importer import NovelImporter


def test_import_from_file_txt():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("第1章\n\n这是第一章的内容。\n\n第2章\n\n这是第二章的内容。")
        path = f.name

    try:
        novel = NovelImporter.from_file(path)
        assert novel.title == os.path.splitext(os.path.basename(path))[0]
        assert len(novel.chapters) == 2
        assert "第一章" in novel.chapters[0]["content"]
        assert novel.chapter_count == 2
    finally:
        os.unlink(path)


def test_import_from_text():
    text = "Content without chapter markers"
    novel = NovelImporter.from_text(text, title="My Novel")
    assert novel.title == "My Novel"
    assert len(novel.chapters) == 1
    assert novel.chapters[0]["content"] == "Content without chapter markers"


def test_import_unsupported_format():
    try:
        NovelImporter.from_file("test.pdf")
        assert False, "Should have raised"
    except ValueError as e:
        assert "Unsupported format" in str(e)


def test_import_with_chapter_markers():
    text = "第1章\n\n开头\n\n第2章\n\n中间\n\n第3章\n\n结尾"
    novel = NovelImporter.from_text(text)
    assert len(novel.chapters) == 3
    assert novel.chapters[0]["number"] == 1
    assert novel.chapters[2]["number"] == 3


def test_import_md_format():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write("第1章\n\nMarkdown chapter content.")
        path = f.name

    try:
        novel = NovelImporter.from_file(path)
        assert len(novel.chapters) == 1
        assert "Markdown chapter content." in novel.chapters[0]["content"]
    finally:
        os.unlink(path)


def test_import_markdown_format():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.markdown', delete=False, encoding='utf-8') as f:
        f.write("第1章\n\nFull markdown extension content.")
        path = f.name

    try:
        novel = NovelImporter.from_file(path)
        assert len(novel.chapters) == 1
    finally:
        os.unlink(path)


def test_import_default_genre():
    novel = NovelImporter.from_text("Some text", title="Test")
    assert novel.genre == "unknown"


def test_import_empty_content():
    novel = NovelImporter.from_text("")
    assert novel.chapter_count == 0


def test_import_rejects_path_traversal():
    """HIGH: Importer must reject path traversal attempts."""
    with pytest.raises(ValueError, match="(?i)path"):
        NovelImporter.from_file("../../../etc/passwd")
