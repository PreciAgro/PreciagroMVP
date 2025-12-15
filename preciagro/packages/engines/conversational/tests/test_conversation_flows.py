import pytest
from fastapi.testclient import TestClient
from ..app import app

client = TestClient(app)


def test_create_session_endpoint():
    response = client.post(
        "/v1/sessions",
        json={
            "user_id": "user1",
            "locale": "en",
            "consent": {
                "consent_id": "c123",
                "use_for_training": False,
                "granted_at": "2023-01-01T00:00:00Z",
                "scope": ["analytics"],
            },
        },
    )
    assert response.status_code == 200
    assert "session_id" in response.json()


def test_send_message_endpoint():
    # 1. Create Session
    create_response = client.post(
        "/v1/sessions",
        json={
            "user_id": "user1",
            "locale": "en",
            "consent": {
                "consent_id": "c123",
                "use_for_training": False,
                "granted_at": "2023-01-01T00:00:00Z",
                "scope": ["analytics"],
            },
        },
    )
    session_id = create_response.json()["session_id"]

    # 2. Send Message
    msg_response = client.post(
        f"/v1/sessions/{session_id}/message",
        json={
            "user_id": "user1",
            "text": "My corn is yellow",
            "locale": "en",
            "consent": {
                "consent_id": "c123",
                "use_for_training": False,
                "granted_at": "2023-01-01T00:00:00Z",
                "scope": ["analytics"],
            },
        },
    )
    assert msg_response.status_code == 200
    data = msg_response.json()
    assert "reply_text" in data
    assert "agrollm_response" in data
    assert "flags" in data
