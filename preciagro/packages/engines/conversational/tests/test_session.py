import pytest
from ..session.session_store import SessionStore

def test_create_session():
    store = SessionStore()
    consent = {
        "consent_id": "c123",
        "use_for_training": False,
        "granted_at": "2023-01-01T00:00:00Z",
        "scope": ["analytics"]
    }
    session_id = store.create_session("user1", "en", consent)
    assert session_id is not None
    
    session = store.get_session(session_id)
    assert session.metadata.user_id == "user1"
    assert session.metadata.consent.use_for_training is False

def test_add_message():
    store = SessionStore()
    consent = {
        "consent_id": "c123",
        "use_for_training": False,
        "granted_at": "2023-01-01T00:00:00Z",
        "scope": ["analytics"]
    }
    session_id = store.create_session("user1", "en", consent)
    
    store.add_message(session_id, "user", "Hello")
    session = store.get_session(session_id)
    assert len(session.history) == 1
    assert session.history[0]["content"] == "Hello"
