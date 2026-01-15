from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool

# Alembic 設定の参照
config = context.config

# ログ設定を読み込む
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Flask-Migrate からメタデータを取得
# ここでターゲットメタデータを指定することで自動生成が可能になる
try:
    target_metadata = current_app.extensions["migrate"].db.metadata
except KeyError:
    target_metadata = None


def get_engine():
    """Flask の SQLAlchemy エンジンを取得する。"""

    try:
        return current_app.extensions["migrate"].db.get_engine()
    except TypeError:
        return current_app.extensions["migrate"].db.engine


def get_engine_url() -> str:
    """エンジン URL を Alembic 用に取得する。"""

    url = get_engine().url
    return str(url).replace("%", "%%")


# SQLAlchemy URL は Flask の設定から注入する
config.set_main_option("sqlalchemy.url", get_engine_url())


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーションを実行する。"""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーションを実行する。"""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
