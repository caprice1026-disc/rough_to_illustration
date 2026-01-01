from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app import create_app
from extensions import db
from models import User
from services.generation_service import GenerationResult


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "INITIAL_USER_USERNAME": None,
            "INITIAL_USER_EMAIL": None,
            "INITIAL_USER_PASSWORD": None,
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        user = User(username="tester", email="tester@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    return client.post(
        "/login",
        data={"username": "tester", "password": "password"},
        follow_redirects=True,
    )


def test_chat_text_action(monkeypatch, client):
    login(client)

    def fake_generate_chat_response(*, contents):
        assert contents
        return "テスト応答"

    monkeypatch.setattr("views.main.generate_chat_response", fake_generate_chat_response)

    response = client.post(
        "/",
        data={
            "mode": "chat_gui",
            "chat_action": "text",
            "chat_message": "こんにちは",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "テスト応答" in response.get_data(as_text=True)


def test_chat_generate_rough(monkeypatch, client):
    login(client)

    fake_result = GenerationResult(
        image_data_uri="data:image/png;base64,AAAA",
        mime_type="image/png",
        image_id="fake-image-id",
    )

    monkeypatch.setattr("views.main.run_generation", lambda **kwargs: fake_result)

    response = client.post(
        "/",
        data={
            "mode": "chat_gui",
            "chat_action": "generate",
            "chat_mode": "rough_with_instructions",
            "chat_color_instruction": "色指定",
            "chat_pose_instruction": "ポーズ指定",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "画像生成が完了しました。" in response.get_data(as_text=True)


def test_chat_generate_reference(monkeypatch, client):
    login(client)

    fake_result = GenerationResult(
        image_data_uri="data:image/png;base64,BBBB",
        mime_type="image/png",
        image_id="fake-image-id-2",
    )

    monkeypatch.setattr("views.main.run_generation_with_reference", lambda **kwargs: fake_result)

    response = client.post(
        "/",
        data={
            "mode": "chat_gui",
            "chat_action": "generate",
            "chat_mode": "reference_style_colorize",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "画像生成が完了しました。" in response.get_data(as_text=True)


def test_chat_generate_edit(monkeypatch, client):
    login(client)

    fake_result = GenerationResult(
        image_data_uri="data:image/png;base64,CCCC",
        mime_type="image/png",
        image_id="fake-image-id-3",
    )

    monkeypatch.setattr("views.main.run_edit_generation", lambda **kwargs: fake_result)

    response = client.post(
        "/",
        data={
            "mode": "chat_gui",
            "chat_action": "generate",
            "chat_mode": "inpaint_outpaint",
            "chat_edit_mode": "inpaint",
            "chat_edit_instruction": "修正",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "画像生成が完了しました。" in response.get_data(as_text=True)


def test_existing_modes_work(monkeypatch, client):
    login(client)

    fake_result = GenerationResult(
        image_data_uri="data:image/png;base64,DDDD",
        mime_type="image/png",
        image_id="fake-image-id-4",
    )

    monkeypatch.setattr("views.main.run_generation", lambda **kwargs: fake_result)
    monkeypatch.setattr("views.main.run_generation_with_reference", lambda **kwargs: fake_result)
    monkeypatch.setattr("views.main.run_edit_generation", lambda **kwargs: fake_result)

    rough_response = client.post(
        "/",
        data={
            "mode": "rough_with_instructions",
            "color_instruction": "色",
            "pose_instruction": "ポーズ",
            "rough_image": (BytesIO(b"fake"), "rough.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert rough_response.status_code == 200

    reference_response = client.post(
        "/",
        data={
            "mode": "reference_style_colorize",
            "reference_image": (BytesIO(b"fake"), "ref.png"),
            "rough_image": (BytesIO(b"fake"), "rough.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert reference_response.status_code == 200

    edit_response = client.post(
        "/",
        data={
            "mode": "inpaint_outpaint",
            "edit_base_image": (BytesIO(b"fake"), "base.png"),
            "edit_mask_data": "data:image/png;base64,AAAA",
            "edit_instruction": "修正",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert edit_response.status_code == 200
