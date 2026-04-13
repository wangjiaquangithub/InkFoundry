"""Pytest fixtures shared across test modules."""
import pytest
from Engine.core.state_db import StateDB


@pytest.fixture
def db_instance():
    """Provide an in-memory StateDB for testing."""
    db = StateDB(":memory:")
    yield db
    db.close()
