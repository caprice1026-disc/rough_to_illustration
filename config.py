from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load .env for local development.
load_dotenv()


def _env(key: str) -> str | None:
    value = os.environ.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_debug(app_env: str) -> bool:
    if app_env.strip().lower() == "production":
        return False
    raw_debug = os.environ.get("APP_DEBUG") or os.environ.get("FLASK_DEBUG")
    if raw_debug is None:
        return True
    return _env_bool(raw_debug)


def _is_production(app_env: str) -> bool:
    return app_env.strip().lower() == "production"


def _normalize_database_url(url: str) -> str:
    if url.startswith("mysql://"):
        return "mysql+pymysql://" + url[len("mysql://") :]
    if url.startswith("mariadb://"):
        return "mariadb+pymysql://" + url[len("mariadb://") :]
    return url


def _build_mysql_url_from_env() -> str | None:
    user = _env("DB_USER")
    password = _env("DB_PASSWORD")
    name = _env("DB_NAME")
    if not user or not name:
        return None

    user_q = quote_plus(user)
    if password is None:
        auth = user_q
    else:
        auth = f"{user_q}:{quote_plus(password)}"

    instance = _env("INSTANCE_CONNECTION_NAME") or _env("CLOUD_SQL_CONNECTION_NAME")
    socket_path = _env("DB_SOCKET")
    host = _env("DB_HOST")
    port = _env("DB_PORT") or "3306"

    if not socket_path and instance:
        socket_path = f"/cloudsql/{instance}"

    name_q = quote_plus(name)
    if socket_path:
        socket_q = quote_plus(socket_path)
        return f"mysql+pymysql://{auth}@/{name_q}?unix_socket={socket_q}"

    if host:
        return f"mysql+pymysql://{auth}@{host}:{port}/{name_q}"

    return None


def _resolve_database_uri(app_env: str) -> str:
    database_url = _env("DATABASE_URL")
    if database_url:
        return _normalize_database_url(database_url)
    mysql_url = _build_mysql_url_from_env()
    if mysql_url:
        return mysql_url
    if _is_production(app_env):
        return ""
    return "sqlite:///app.db"


def _resolve_engine_options(app_env: str) -> dict[str, object]:
    if not _is_production(app_env):
        return {}

    return {
        "pool_pre_ping": True,
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "280")),
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "30")),
    }


def _resolve_chat_image_storage(app_env: str) -> str:
    explicit = _env("CHAT_IMAGE_STORAGE")
    if explicit:
        return explicit.lower()
    if _is_production(app_env):
        return "gcs"
    return "local"


class Config:
    """Flask app settings loaded from environment variables."""

    APP_ENV = os.environ.get("APP_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(APP_ENV)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _resolve_engine_options(APP_ENV)
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
    CHAT_IMAGE_STORAGE = _resolve_chat_image_storage(APP_ENV)
    CHAT_IMAGE_DIR = os.environ.get("CHAT_IMAGE_DIR", "chat_images")
