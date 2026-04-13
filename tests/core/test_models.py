"""Tests for Pydantic state models."""
import pytest
from Engine.core.models import CharacterState, WorldState, StateSnapshot


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
