"""Pydantic models for narrative state."""
from __future__ import annotations

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
