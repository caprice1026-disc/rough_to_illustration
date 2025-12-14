from __future__ import annotations

from typing import Optional

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

    def set_password(self, raw_password: str) -> None:
        """平文パスワードを安全なハッシュに変換して保存する。"""

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """入力パスワードと保存済みハッシュを照合する。"""

        return check_password_hash(self.password_hash, raw_password)


class IllustrationPreset(db.Model):
    """ユーザーに紐づく色・ポーズのプリセット。"""

    __tablename__ = "illustration_presets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    color_instruction = db.Column(db.String(200), nullable=False)
    pose_instruction = db.Column(db.String(160), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="presets")


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """ログインセッションからユーザーを復元する。"""

    if user_id is None:
        return None
    return User.query.get(int(user_id))
