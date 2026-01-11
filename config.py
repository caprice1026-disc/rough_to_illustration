from __future__ import annotations

import os

from dotenv import load_dotenv

# .env を読み込んで環境変数を初期化する
load_dotenv()


def _env_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_debug(app_env: str) -> bool:
    if app_env.strip().lower() == "production":
        return False
    raw_debug = os.environ.get("APP_DEBUG")
    if raw_debug is None:
        raw_debug = os.environ.get("FLASK_DEBUG")
    if raw_debug is None:
        return True
    return _env_bool(raw_debug)


def _is_production(app_env: str) -> bool:
    return app_env.strip().lower() == "production"


def _resolve_database_uri(app_env: str) -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url
    if _is_production(app_env):
        return ""
    return "sqlite:///app.db"


class Config:
    """Flaskアプリの設定値をまとめたクラス。"""

    APP_ENV = os.environ.get("APP_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(APP_ENV)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(32 * 1024 * 1024)))
    MAX_FORM_MEMORY_SIZE = int(os.environ.get("MAX_FORM_MEMORY_SIZE", str(32 * 1024 * 1024)))
    MAX_IMAGE_WIDTH = int(os.environ.get("MAX_IMAGE_WIDTH", "8192"))
    MAX_IMAGE_HEIGHT = int(os.environ.get("MAX_IMAGE_HEIGHT", "8192"))
    MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", str(64 * 1024 * 1024)))
    DEBUG = _resolve_debug(APP_ENV)
    SESSION_COOKIE_SECURE = _is_production(APP_ENV)
    SESSION_COOKIE_HTTPONLY = _is_production(APP_ENV)
    PREFERRED_URL_SCHEME = "https" if _is_production(APP_ENV) else "http"
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    INITIAL_USER_USERNAME = os.environ.get("INITIAL_USER_USERNAME")
    INITIAL_USER_EMAIL = os.environ.get("INITIAL_USER_EMAIL")
    INITIAL_USER_PASSWORD = os.environ.get("INITIAL_USER_PASSWORD")
    CHAT_IMAGE_BUCKET = os.environ.get("CHAT_IMAGE_BUCKET")
