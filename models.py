from __future__ import annotations

from typing import Optional

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


class User(db.Model, UserMixin):
    """アプリ利用者を表すモデル。"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    presets = db.relationship(
        "IllustrationPreset",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_sessions = db.relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, raw_password: str) -> None:
        """平文パスワードを安全なハッシュに変換して保存する。"""

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """入力パスワードと保存済みハッシュを照合する。"""

        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_initial_user(self) -> bool:
        """イニシャルユーザーかどうかを判定する。"""

        username = current_app.config.get("INITIAL_USER_USERNAME")
        email = current_app.config.get("INITIAL_USER_EMAIL")
        if not username or not email:
            return False
        return self.username == username and self.email == email


class IllustrationPreset(db.Model):
    """ユーザーに紐づく色・ポーズのプリセット。"""

    __tablename__ = "illustration_presets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    color_instruction = db.Column(db.String(1000), nullable=False)
    pose_instruction = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="presets")


class ChatSession(db.Model):
    """チャットセッションを表すモデル。"""

    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    user = db.relationship("User", back_populates="chat_sessions")
    messages = db.relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(db.Model):
    """チャット内の1メッセージを表すモデル。"""

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text)
    mode_id = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    session = db.relationship("ChatSession", back_populates="messages")
    attachments = db.relationship(
        "ChatAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ChatAttachment(db.Model):
    """チャットメッセージに紐づく画像ファイル。"""

    __tablename__ = "chat_attachments"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    kind = db.Column(db.String(40), nullable=False)
    image_id = db.Column(db.String(120), nullable=False)
    mime_type = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    message = db.relationship("ChatMessage", back_populates="attachments")


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """ログインセッションからユーザーを復元する。"""

    if user_id is None:
        return None
    return User.query.get(int(user_id))
