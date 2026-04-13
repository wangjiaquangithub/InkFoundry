import pytest
import threading
from Engine.core.state_db import StateDB
from Engine.core.filter import StateFilter


@pytest.fixture
def db(tmp_path):
    """Create a StateDB instance with a temporary SQLite file."""
    db_path = tmp_path / "test_state.db"
    return StateDB(str(db_path))


def test_init_creates_tables(db):
    """Test that StateDB initializes with correct schema."""
    state = db.get_state("nonexistent_key")
    assert state is None


def test_get_and_update_state(db):
    """Test basic get and update operations."""
    db.update_state("chapter_1", {"status": "draft", "word_count": 100})
    result = db.get_state("chapter_1")
    assert result is not None
    assert result["status"] == "draft"
    assert result["word_count"] == 100


def test_update_state_overwrites(db):
    """Test that update_state overwrites existing state."""
    db.update_state("chapter_1", {"status": "draft"})
    db.update_state("chapter_1", {"status": "reviewed"})
    result = db.get_state("chapter_1")
    assert result["status"] == "reviewed"


def test_update_state_with_version(db):
    """Test optimistic locking with version field."""
    db.update_state("chapter_1", {"status": "draft", "version": 1})
    result = db.get_state("chapter_1")
    assert result["version"] == 1

    # Update with correct version should succeed
    db.update_state("chapter_1", {"status": "reviewed", "version": 2}, expected_version=1)
    result = db.get_state("chapter_1")
    assert result["version"] == 2


def test_update_state_version_mismatch(db):
    """Test that version mismatch raises error."""
    db.update_state("chapter_1", {"status": "draft", "version": 1})
    # Wrong expected version should raise
    with pytest.raises(ValueError, match="(?i)version"):
        db.update_state(
            "chapter_1", {"status": "reviewed", "version": 2}, expected_version=99
        )


def test_atomic_lock(db):
    """Test that atomic lock prevents concurrent writes."""
    db.update_state("chapter_1", {"status": "draft"}, lock_id="lock_a")

    # Same lock should allow update
    db.update_state("chapter_1", {"status": "editing"}, lock_id="lock_a")

    # Different lock on same key should fail
    with pytest.raises(RuntimeError, match="locked"):
        db.update_state("chapter_1", {"status": "reviewed"}, lock_id="lock_b")


def test_lock_release(db):
    """Test that lock can be released."""
    db.update_state("chapter_1", {"status": "draft"}, lock_id="lock_a")
    db.release_lock("chapter_1", lock_id="lock_a")

    # After release, different lock should succeed
    db.update_state("chapter_1", {"status": "reviewed"}, lock_id="lock_b")
    result = db.get_state("chapter_1")
    assert result["status"] == "reviewed"


def test_concurrent_write_threads(db):
    """Test atomic behavior under concurrent access."""
    results = {"success": 0, "failed": 0}
    barrier = threading.Barrier(2)

    def writer(lock_id):
        barrier.wait()
        try:
            db.update_state("shared_key", {"writer": lock_id}, lock_id=lock_id)
            results["success"] += 1
        except RuntimeError:
            results["failed"] += 1

    t1 = threading.Thread(target=writer, args=("lock_1",))
    t2 = threading.Thread(target=writer, args=("lock_2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["success"] == 1
    assert results["failed"] == 1


def test_state_filter_rag_conflict():
    """Test StateFilter blocks on RAG conflict."""
    sf = StateFilter()
    # When RAG data conflicts with StateDB state, should block
    state_db_data = {"character": "Alice", "trait": "brave"}
    rag_data = {"character": "Alice", "trait": "cowardly"}

    result = sf.check_conflict(state_db_data, rag_data)
    assert result["conflict"] is True
    assert result["blocked"] is True


def test_state_filter_no_conflict():
    """Test StateFilter passes when no conflict."""
    sf = StateFilter()
    state_db_data = {"character": "Alice", "trait": "brave"}
    rag_data = {"character": "Alice", "trait": "brave"}

    result = sf.check_conflict(state_db_data, rag_data)
    assert result["conflict"] is False
    assert result["blocked"] is False


def test_state_filter_partial_conflict():
    """Test StateFilter detects partial conflicts."""
    sf = StateFilter()
    state_db_data = {"character": "Alice", "trait": "brave", "age": 25}
    rag_data = {"character": "Alice", "trait": "brave", "age": 30}

    result = sf.check_conflict(state_db_data, rag_data)
    assert result["conflict"] is True
    assert "age" in result["conflicting_keys"]


def test_close(db):
    """Test that close releases resources."""
    db.update_state("key", {"value": 1})
    db.close()
    # After close, operations should raise
    with pytest.raises(RuntimeError):
        db.get_state("key")
