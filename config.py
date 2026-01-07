from __future__ import annotations

import os

from dotenv import load_dotenv

# .env を読み込んで環境変数を初期化する
load_dotenv()


class Config:
    """Flaskアプリの設定値をまとめたクラス。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(128 * 1024 * 1024)))
    MAX_FORM_MEMORY_SIZE = int(os.environ.get("MAX_FORM_MEMORY_SIZE", str(128 * 1024 * 1024)))
    MAX_IMAGE_WIDTH = int(os.environ.get("MAX_IMAGE_WIDTH", "8192"))
    MAX_IMAGE_HEIGHT = int(os.environ.get("MAX_IMAGE_HEIGHT", "8192"))
    MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", str(64 * 1024 * 1024)))
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    INITIAL_USER_USERNAME = os.environ.get("INITIAL_USER_USERNAME")
    INITIAL_USER_EMAIL = os.environ.get("INITIAL_USER_EMAIL")
    INITIAL_USER_PASSWORD = os.environ.get("INITIAL_USER_PASSWORD")
