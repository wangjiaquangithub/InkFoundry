"""Pydantic models for narrative state."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CharacterState(BaseModel):
    """Represents the current state of a character in the narrative."""
    name: str
    role: str
    status: str = "active"

    @property
    def is_alive(self) -> bool:
        return self.status not in ("deceased", "inactive")


class WorldState(BaseModel):
    """Represents the state of a location or world element."""
    name: str
    description: str = ""
    state: str = "normal"


class StateSnapshot(BaseModel):
    """A versioned snapshot of all narrative state at a point in time."""
    version: int
    chapter_num: int
    characters: List[CharacterState] = Field(default_factory=list)
    world_states: List[WorldState] = Field(default_factory=list)
    summary: str = ""
    metadata: dict = Field(default_factory=dict)


class Outline(BaseModel):
    """Novel outline with story structure."""
    title: str
    summary: str
    total_chapters: int = 100
    arc: str = "hero_journey"  # hero_journey, three_act, five_act
    volume_plans: List[dict] = Field(default_factory=list)
    chapter_summaries: List[dict] = Field(default_factory=list)
    tension_curve: List[int] = Field(default_factory=list)
    foreshadowing: List[dict] = Field(default_factory=list)
    genre_rules: List[str] = Field(default_factory=list)


class Chapter(BaseModel):
    """A single chapter in the novel."""
    chapter_num: int
    title: str = ""
    content: str = ""
    status: str = "pending"  # pending, draft, reviewed, final, rejected
    word_count: int = 0
    tension_level: int = 5
    version: int = 1
    review_notes: str = ""
    agent_results: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CharacterProfile(BaseModel):
    """Detailed character profile beyond basic state."""
    name: str
    gender: str = ""
    age: int = 0
    appearance: str = ""
    personality: str = ""
    backstory: str = ""
    motivation: str = ""
    voice_profile_ref: str = "default"


class CharacterRelationship(BaseModel):
    """Relationship between two characters."""
    from_character: str
    to_character: str
    relationship_type: str  # parent, child, mentor, friend, enemy, lover, etc.
    description: str = ""
    strength: float = 0.5  # 0.0-1.0


class WorldBuilding(BaseModel):
    """Detailed world building settings."""
    name: str
    era: str = ""
    geography: str = ""
    social_structure: str = ""
    technology_level: str = ""
    cultures: List[dict] = Field(default_factory=list)
    factions: List[dict] = Field(default_factory=list)


class PowerSystem(BaseModel):
    """Power/cultivation system definition."""
    name: str
    levels: List[str] = Field(default_factory=list)
    rules: str = ""


class Timeline(BaseModel):
    """Timeline of major events."""
    year: int
    event: str
    impact: str = ""
