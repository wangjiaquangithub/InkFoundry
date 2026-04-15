"""Tests for Pydantic state models."""
import pytest
from Engine.core.models import (
    CharacterState, WorldState, StateSnapshot,
    Outline, Chapter, CharacterProfile, CharacterRelationship,
    WorldBuilding, PowerSystem, Timeline,
)


def test_create_character():
    char = CharacterState(name="Hero", role="Protagonist")
    assert char.name == "Hero"
    assert char.role == "Protagonist"
    assert char.status == "active"


def test_character_default_status():
    char = CharacterState(name="Test", role="Support")
    assert char.status == "active"


def test_character_with_custom_status():
    char = CharacterState(name="Villain", role="Antagonist", status="deceased")
    assert char.status == "deceased"


def test_character_is_active_property():
    active = CharacterState(name="A", role="Protagonist")
    deceased = CharacterState(name="B", role="Villain", status="deceased")
    inactive = CharacterState(name="C", role="Support", status="inactive")
    assert active.is_alive is True
    assert deceased.is_alive is False
    assert inactive.is_alive is False


def test_world_state():
    world = WorldState(
        name="Royal Palace",
        description="A grand palace in the capital",
        state="intact"
    )
    assert world.name == "Royal Palace"
    assert world.state == "intact"


def test_world_state_default_values():
    world = WorldState(name="Forest")
    assert world.state == "normal"
    assert world.description == ""


def test_state_snapshot():
    snapshot = StateSnapshot(
        version=1,
        chapter_num=5,
        characters=[
            CharacterState(name="Hero", role="Protagonist"),
            CharacterState(name="Villain", role="Antagonist", status="deceased"),
        ],
        world_states=[WorldState(name="Palace", state="damaged")],
        summary="Hero defeated the villain."
    )
    assert snapshot.version == 1
    assert snapshot.chapter_num == 5
    assert len(snapshot.characters) == 2
    assert snapshot.summary == "Hero defeated the villain."


# --- New model tests for Phase 0 ---

def test_outline_model():
    outline = Outline(
        title="My Novel",
        summary="A story about adventure",
        total_chapters=100,
        arc="hero_journey",
    )
    assert outline.title == "My Novel"
    assert outline.total_chapters == 100
    assert outline.genre_rules == []


def test_chapter_model():
    chapter = Chapter(
        chapter_num=1,
        title="Chapter 1",
        content="Once upon a time...",
        status="draft",
        word_count=3000,
    )
    assert chapter.chapter_num == 1
    assert chapter.status == "draft"
    assert chapter.version == 1


def test_character_profile_model():
    profile = CharacterProfile(
        name="Hero",
        gender="male",
        age=25,
        appearance="tall with dark hair",
        personality="brave and stubborn",
        backstory="Orphaned as a child...",
        motivation="Find the truth about parents",
        voice_profile_ref="default",
    )
    assert profile.name == "Hero"
    assert profile.voice_profile_ref == "default"


def test_character_relationship_model():
    rel = CharacterRelationship(
        from_character="Hero",
        to_character="Mentor",
        relationship_type="mentor",
        description="Wise old teacher",
        strength=0.8,
    )
    assert rel.from_character == "Hero"
    assert rel.relationship_type == "mentor"
    assert rel.strength == 0.8


def test_world_building_model():
    wb = WorldBuilding(
        name="Default World",
        era="ancient",
        geography="mountains and rivers",
        social_structure="feudal kingdom",
        technology_level="medieval",
    )
    assert wb.era == "ancient"


def test_power_system_model():
    ps = PowerSystem(
        name="Cultivation",
        levels=["Qi Condensation", "Foundation", "Golden Core", "Nascent Soul"],
        rules="Cannot skip levels",
    )
    assert len(ps.levels) == 4


def test_timeline_model():
    tl = Timeline(
        year=1,
        event="The Great War began",
        impact="Changed the world forever",
    )
    assert tl.year == 1
