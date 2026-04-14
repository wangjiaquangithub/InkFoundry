"""Novel import and resume from text files."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


def _validate_input_path(file_path: str) -> None:
    """Reject path traversal attempts."""
    if ".." in file_path.split(os.sep) or ".." in file_path.replace("\\", "/").split("/"):
        raise ValueError(f"Invalid input path: {file_path}")


@dataclass
class ImportedNovel:
    """A novel imported from a text file with parsed chapters."""
    title: str
    chapters: list[dict] = field(default_factory=list)  # [{"number": 1, "content": "..."}]
    genre: str = "unknown"

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


class NovelImporter:
    """Import and resume novels from text-based file formats."""

    SUPPORTED_FORMATS = (".txt", ".md", ".markdown")

    @staticmethod
    def from_file(file_path: str) -> ImportedNovel:
        """Import a novel from a text file.

        Args:
            file_path: Path to the text file (.txt, .md, .markdown).

        Returns:
            ImportedNovel with parsed chapters.

        Raises:
            ValueError: If the file format is not supported.
        """
        _validate_input_path(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in NovelImporter.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {ext}. Supported: {NovelImporter.SUPPORTED_FORMATS}"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        title = os.path.splitext(os.path.basename(file_path))[0]
        chapters = NovelImporter._parse_chapters(content)

        return ImportedNovel(title=title, chapters=chapters)

    @staticmethod
    def from_text(text: str, title: str = "Untitled") -> ImportedNovel:
        """Import a novel from a text string.

        Args:
            text: The novel content as a string.
            title: Optional title for the novel.

        Returns:
            ImportedNovel with parsed chapters.
        """
        chapters = NovelImporter._parse_chapters(text)
        return ImportedNovel(title=title, chapters=chapters)

    @staticmethod
    def _parse_chapters(content: str) -> list[dict]:
        """Parse chapter markers from content.

        Supports markers like "第X章", "Chapter X", "## Chapter X".
        Chapter markers must appear at the start of a line to avoid matching
        chapter-like text embedded in prose (e.g., "这是第一章的内容").

        Args:
            content: Full novel text content.

        Returns:
            List of chapter dicts with "number" and "content" keys.
        """
        pattern = r'^(?:第[\d一二三四五六七八九十百]+章|Chapter\s+\d+|##\s+Chapter\s+\d+)'
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        # No chapter markers found — treat entire content as one chapter
        if not matches:
            stripped = content.strip()
            if stripped:
                return [{"number": 1, "content": stripped}]
            return []

        # Extract content between chapter markers
        chapters = []
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            text = content[start:end].strip()
            if text:
                chapters.append({"number": len(chapters) + 1, "content": text})

        return chapters
