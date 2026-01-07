from __future__ import annotations

import json

import pytest

from app import create_app
from extensions import db
from models import ChatMessage, ChatSession, User


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        user = User(username="tester", email="tester@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    csrf_token = get_csrf_token(client)
    return client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "password123"},
        headers={"X-CSRFToken": csrf_token},
    )


def get_csrf_token(client):
    response = client.get("/api/csrf")
    payload = json.loads(response.data)
    return payload["csrf_token"]


def test_chat_page_creates_session(client, app):
    login(client)
    response = client.get("/api/chat/sessions")
    assert response.status_code == 200

    with app.app_context():
        sessions = ChatSession.query.all()
        assert len(sessions) == 1
        assert sessions[0].title == "新しいチャット"


def test_index_page_loads_for_logged_in_user(client):
    login(client)
    response = client.get("/")
    assert response.status_code == 200
    assert "static/spa/app.js" in response.get_data(as_text=True)


def test_text_chat_persists_messages(client, app, monkeypatch):
    login(client)

    with app.app_context():
        session = ChatSession(user_id=User.query.first().id, title="新しいチャット")
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    monkeypatch.setattr("services.chat_service.generate_text_reply", lambda *_: "テスト応答")

    response = client.post(
        "/api/chat/messages",
        data={"session_id": session_id, "mode_id": "text_chat", "message": "こんにちは"},
        headers={"X-CSRFToken": get_csrf_token(client)},
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["assistant"]["text"] == "テスト応答"

    with app.app_context():
        messages = (
            ChatMessage.query.filter_by(session_id=session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        assert len(messages) == 2
        roles = [message.role for message in messages]
        assert roles == ["user", "assistant"]
