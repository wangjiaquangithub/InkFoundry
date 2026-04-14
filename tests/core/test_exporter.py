"""Tests for Novel Exporter."""
from __future__ import annotations

import tempfile
import os

from Engine.core.exporter import NovelExporter


def test_export_to_txt():
    novel = {
        "title": "Test Novel",
        "chapters": [
            {"number": 1, "content": "Chapter one content"},
            {"number": 2, "content": "Chapter two content"},
        ],
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        path = f.name

    try:
        NovelExporter.to_txt(novel, path)
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert "Test Novel" in content
        assert "第1章" in content
        assert "Chapter one content" in content
    finally:
        os.unlink(path)


def test_export_to_markdown():
    novel = {
        "title": "MD Novel",
        "chapters": [{"number": 1, "content": "Content here"}],
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        path = f.name

    try:
        NovelExporter.to_markdown(novel, path)
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert "# MD Novel" in content
        assert "## 第1章" in content
    finally:
        os.unlink(path)


def test_export_to_html():
    novel = {
        "title": "HTML Novel",
        "chapters": [{"number": 1, "content": "Chapter content\nLine 2"}],
    }
    html = NovelExporter._to_html(novel)
    assert "HTML Novel" in html
    assert "第1章" in html
    assert "Chapter content" in html
    assert "<br/>" in html


def test_export_to_txt_creates_directory():
    novel = {
        "title": "Nested Novel",
        "chapters": [{"number": 1, "content": "Content"}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "subdir", "novel.txt")
        NovelExporter.to_txt(novel, path)
        assert os.path.exists(path)
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert "Nested Novel" in content


def test_export_to_markdown_creates_directory():
    novel = {
        "title": "Deep Novel",
        "chapters": [{"number": 1, "content": "Content"}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "a", "b", "novel.md")
        NovelExporter.to_markdown(novel, path)
        assert os.path.exists(path)


def test_export_to_epub():
    novel = {
        "title": "EPUB Novel",
        "chapters": [
            {"number": 1, "content": "Chapter one"},
            {"number": 2, "content": "Chapter two"},
        ],
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.epub', delete=False, encoding='utf-8') as f:
        path = f.name

    try:
        NovelExporter.to_epub(novel, path)
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert "EPUB Novel" in content
        assert "<!DOCTYPE html>" in content
        assert "第1章" in content
        assert "第2章" in content
    finally:
        os.unlink(path)


def test_export_html_escapes_special_characters():
    novel = {
        "title": "Special <Title> & \"Quotes\"",
        "chapters": [{"number": 1, "content": "Content with <html> & special chars"}],
    }
    html = NovelExporter._to_html(novel)
    assert "&lt;Title&gt;" in html
    assert "&amp;" in html
    assert "&lt;html&gt;" in html


def test_export_default_title():
    novel = {"chapters": [{"number": 1, "content": "Content"}]}
    html = NovelExporter._to_html(novel)
    assert "Untitled" in html


def test_export_empty_chapters():
    novel = {"title": "Empty", "chapters": []}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        path = f.name

    try:
        NovelExporter.to_txt(novel, path)
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert "Empty" in content
    finally:
        os.unlink(path)
