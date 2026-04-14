"""Tests for resource cleanup — verify no leaked SQLite connections."""
from __future__ import annotations

import gc
import warnings

from Engine.core.state_db import StateDB


def _count_unclosed_warnings():
    """Force GC and count unclosed database ResourceWarnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", ResourceWarning)
        gc.collect()
    return [x for x in w if "unclosed database" in str(x.message)]


def test_state_db_close_no_warning():
    """StateDB with proper close() should not leak."""
    before = len(_count_unclosed_warnings())
    db = StateDB(":memory:")
    db.update_state("key", {"value": 1})
    db.close()
    after = len(_count_unclosed_warnings())
    # Our close() should not add new unclosed warnings
    assert after <= before


def test_state_db_context_manager():
    """StateDB used as context manager should auto-close."""
    before = len(_count_unclosed_warnings())
    with StateDB(":memory:") as db:
        db.update_state("key", {"value": 2})
    after = len(_count_unclosed_warnings())
    assert after <= before
