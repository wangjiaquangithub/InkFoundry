"""Genre-specific validation rules for novel content."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class GenreRule:
    name: str
    max_chapter_length: int = 5000
    min_chapter_length: int = 500
    required_elements: list[str] = field(default_factory=list)
    forbidden_elements: list[str] = field(default_factory=list)
    tone: str = "neutral"


# Genre configurations
GENRE_CONFIGS: dict[str, GenreRule] = {
    "xuanhuan": GenreRule(
        name="玄幻",
        max_chapter_length=8000,
        min_chapter_length=1000,
        required_elements=["修炼", "境界", "功法"],
        forbidden_elements=["现代科技", "智能手机"],
        tone="epic",
    ),
    "xianxia": GenreRule(
        name="仙侠",
        max_chapter_length=6000,
        min_chapter_length=800,
        required_elements=["灵气", "丹药", "法宝"],
        forbidden_elements=["枪械", "汽车"],
        tone="poetic",
    ),
    "romance": GenreRule(
        name="言情",
        max_chapter_length=5000,
        min_chapter_length=500,
        required_elements=["情感描写"],
        forbidden_elements=["大规模战争"],
        tone="emotional",
    ),
    "scifi": GenreRule(
        name="科幻",
        max_chapter_length=10000,
        min_chapter_length=800,
        required_elements=["科技元素"],
        forbidden_elements=[],
        tone="rational",
    ),
    "wuxia": GenreRule(
        name="武侠",
        max_chapter_length=6000,
        min_chapter_length=800,
        required_elements=["武功", "江湖"],
        forbidden_elements=["现代武器", "飞机大炮"],
        tone="classic",
    ),
}


class GenreValidator:
    @staticmethod
    def validate_chapter(genre: str, content: str) -> list[str]:
        """Validate a chapter against genre rules. Returns list of issues."""
        rule = GENRE_CONFIGS.get(genre)
        if not rule:
            return [f"Unknown genre: {genre}. Supported: {list(GENRE_CONFIGS.keys())}"]

        issues = []

        # Length checks
        length = len(content)
        if length < rule.min_chapter_length:
            issues.append(f"章节太短({length}字)，至少{rule.min_chapter_length}字")
        if length > rule.max_chapter_length:
            issues.append(f"章节太长({length}字)，最多{rule.max_chapter_length}字")

        # Required element checks
        for element in rule.required_elements:
            if element not in content:
                issues.append(f"缺少{rule.name}元素: {element}")

        # Forbidden element checks
        for forbidden in rule.forbidden_elements:
            if forbidden in content:
                issues.append(f"包含禁用的{rule.name}元素: {forbidden}")

        return issues

    @staticmethod
    def list_genres() -> list[str]:
        return list(GENRE_CONFIGS.keys())

    @staticmethod
    def get_genre_info(genre: str) -> GenreRule | None:
        return GENRE_CONFIGS.get(genre)
