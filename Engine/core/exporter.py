"""Novel export to TXT, Markdown, and EPUB formats."""
from __future__ import annotations

import os
from html import escape
from typing import Optional


class NovelExporter:
    """Export novels to plain text, Markdown, and HTML/EPUB formats."""

    SUPPORTED_FORMATS = (".txt", ".md", ".epub")

    @staticmethod
    def to_txt(novel: dict, file_path: str) -> None:
        """Export novel as plain text.

        Args:
            novel: Dict with "title" and "chapters" keys.
            file_path: Output file path.
        """
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {novel.get('title', 'Untitled')}\n\n")
            for chapter in novel.get("chapters", []):
                f.write(f"第{chapter.get('number', '?')}章\n\n")
                f.write(chapter.get("content", ""))
                f.write("\n\n")

    @staticmethod
    def to_markdown(novel: dict, file_path: str) -> None:
        """Export novel as Markdown.

        Args:
            novel: Dict with "title" and "chapters" keys.
            file_path: Output file path.
        """
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {novel.get('title', 'Untitled')}\n\n")
            for chapter in novel.get("chapters", []):
                f.write(f"## 第{chapter.get('number', '?')}章\n\n")
                f.write(chapter.get("content", ""))
                f.write("\n\n")

    @staticmethod
    def to_epub(novel: dict, file_path: str) -> None:
        """Export novel as simplified EPUB (HTML fallback).

        Note: A full EPUB implementation requires ZIP and OCF packaging.
        This creates a minimal HTML file that can be converted to EPUB later.

        Args:
            novel: Dict with "title" and "chapters" keys.
            file_path: Output file path.
        """
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        html_content = NovelExporter._to_html(novel)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    @staticmethod
    def _to_html(novel: dict) -> str:
        """Convert novel to HTML representation.

        Args:
            novel: Dict with "title" and "chapters" keys.

        Returns:
            HTML string with escaped content.
        """
        title = escape(novel.get("title", "Untitled"))
        chapters_html = ""
        for chapter in novel.get("chapters", []):
            content = escape(chapter.get("content", "")).replace("\n", "<br/>\n")
            chapters_html += (
                f'<div class="chapter">\n'
                f'    <h2>第{chapter.get("number", "?")}章</h2>\n'
                f'    <div class="content">{content}</div>\n'
                f"</div>\n"
            )

        return (
            f"<!DOCTYPE html>\n"
            f'<html lang="zh">\n'
            f"<head>\n"
            f'    <meta charset="UTF-8">\n'
            f"    <title>{title}</title>\n"
            f"</head>\n"
            f"<body>\n"
            f"    <h1>{title}</h1>\n"
            f"    {chapters_html}"
            f"</body>\n"
            f"</html>"
        )
