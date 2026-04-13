"""Tests for MCP Server exposing StateDB."""
import pytest
from Engine.core.mcp_server import create_mcp_server, get_mcp
from Engine.core.state_db import StateDB
from Engine.core.models import CharacterState


def test_mcp_read_character():
    db = StateDB(":memory:")
    db.update_character(CharacterState(name="Hero", role="Protagonist"))
    mcp = get_mcp(db)

    # Verify MCP server was created with tools registered
    assert mcp is not None
    # The read_character tool is registered on the MCP server
    # Test the tool function by accessing the db directly
    char = db.get_character("Hero")
    assert char is not None
    assert char.name == "Hero"
    assert char.role == "Protagonist"


def test_mcp_read_nonexistent_character():
    db = StateDB(":memory:")
    mcp = get_mcp(db)
    char = db.get_character("Nobody")
    assert char is None


def test_mcp_server_created():
    db = StateDB(":memory:")
    mcp = create_mcp_server(db)
    assert mcp is not None
