"""MCP Server exposing StateDB operations via standard MCP protocol."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from Engine.core.state_db import StateDB

# Module-level instances (used when running as standalone server)
_mcp: FastMCP | None = None
_db: StateDB | None = None


def get_mcp(db: StateDB) -> FastMCP:
    """Get or create the MCP server with the given StateDB."""
    mcp = FastMCP("InkFoundryState")

    @mcp.tool()
    def read_character(name: str) -> str:
        """Read a character's state from StateDB."""
        char = db.get_character(name)
        return char.model_dump_json() if char else "Not Found"

    @mcp.tool()
    def list_characters() -> str:
        """List all character names in StateDB."""
        cursor = db.conn.execute("SELECT name FROM characters")
        names = [row[0] for row in cursor.fetchall()]
        return ", ".join(names) if names else "No characters"

    return mcp


def create_mcp_server(db: StateDB) -> FastMCP:
    """Factory function for testing - creates MCP server with given db."""
    return get_mcp(db)


# Convenience function for tool import
def read_character(name: str) -> str:
    """Read a character's state (for direct import in tests)."""
    global _db
    if _db is None:
        _db = StateDB()
    char = _db.get_character(name)
    return char.model_dump_json() if char else "Not Found"
