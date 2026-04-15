import pytest
import threading
from Engine.core.state_db import StateDB
from Engine.core.filter import StateFilter
from Engine.core.models import (
    Chapter, Outline, CharacterProfile, CharacterRelationship,
    WorldBuilding, PowerSystem, Timeline,
)


@pytest.fixture
def db(tmp_path):
    """Create a StateDB instance with a temporary SQLite file."""
    db_path = tmp_path / "test_state.db"
    db = StateDB(str(db_path))
    yield db
    db.close()


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


# --- Phase 0: New table tests ---

def test_update_and_retrieve_chapter(db):
    chapter = Chapter(
        chapter_num=1,
        title="第一章",
        content="Test content",
        status="draft",
        word_count=3000,
    )
    db.update_chapter(chapter)
    retrieved = db.get_chapter(1)
    assert retrieved is not None
    assert retrieved.chapter_num == 1
    assert retrieved.title == "第一章"
    assert retrieved.content == "Test content"
    assert retrieved.status == "draft"


def test_update_chapter_increments_version(db):
    chapter = Chapter(chapter_num=1, title="v1", content="v1")
    db.update_chapter(chapter)
    ch1 = db.get_chapter(1)
    assert ch1.version == 1

    chapter.content = "v2 content"
    db.update_chapter(chapter)
    ch2 = db.get_chapter(1)
    assert ch2.version == 2
    assert ch2.content == "v2 content"


def test_list_chapters(db):
    for i in range(1, 4):
        db.update_chapter(Chapter(chapter_num=i, content=f"Content {i}"))
    chapters = db.list_chapters()
    assert len(chapters) == 3
    assert chapters[0].chapter_num == 1


def test_delete_chapter(db):
    db.update_chapter(Chapter(chapter_num=1, content="test"))
    result = db.delete_chapter(1)
    assert result is True
    assert db.get_chapter(1) is None


def test_save_and_retrieve_outline(db):
    outline = Outline(
        title="My Novel",
        summary="A great story",
        total_chapters=50,
    )
    db.save_outline(outline)
    retrieved = db.get_outline()
    assert retrieved is not None
    assert retrieved.title == "My Novel"
    assert retrieved.total_chapters == 50


def test_save_character_profile(db):
    profile = CharacterProfile(
        name="Hero",
        personality="brave",
        backstory="Orphan",
    )
    db.save_character_profile(profile)
    retrieved = db.get_character_profile("Hero")
    assert retrieved is not None
    assert retrieved.name == "Hero"
    assert retrieved.personality == "brave"


def test_add_character_relationship(db):
    rel = CharacterRelationship(
        from_character="Hero",
        to_character="Mentor",
        relationship_type="mentor",
        strength=0.8,
    )
    db.add_character_relationship(rel)
    rels = db.get_character_relationships("Hero")
    assert len(rels) == 1
    assert rels[0].to_character == "Mentor"


def test_save_world_building(db):
    wb = WorldBuilding(name="My World", era="ancient")
    db.save_world_building(wb)
    retrieved = db.get_world_building()
    assert retrieved is not None
    assert retrieved.name == "My World"
    assert retrieved.era == "ancient"


def test_add_power_system(db):
    ps = PowerSystem(name="Cultivation", levels=["Qi", "Foundation", "Core"])
    db.add_power_system(ps)
    systems = db.get_power_systems()
    assert len(systems) == 1
    assert systems[0].name == "Cultivation"


def test_add_timeline_event(db):
    tl = Timeline(year=1, event="The beginning")
    db.add_timeline_event(tl)
    events = db.get_timeline()
    assert len(events) == 1
    assert events[0].year == 1
    assert events[0].event == "The beginning"
