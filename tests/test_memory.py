import pytest
from app.memory import store


def test_create_session():
    """Test session creation."""
    store.create_session("test_001")
    sessions = store.get_recent_sessions(1)
    assert len(sessions) >= 1


def test_add_task():
    task_id = store.add_task("Test task")
    assert task_id > 0
    
    tasks = store.get_tasks(done=False)
    assert any(t["description"] == "Test task" for t in tasks)


def test_save_fact():
    fact_id = store.save_fact("test", "This is a test fact")
    assert fact_id > 0
    
    facts = store.get_facts(category="test")
    assert len(facts) >= 1


def test_search_turns():
    store.add_turn("test_001", "user", "Hello world")
    results = store.search_turns("Hello", limit=5)
    assert isinstance(results, list)