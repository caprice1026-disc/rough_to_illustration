from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from flask import current_app

config = context.config

if config.config_file_name is None:
    config.config_file_name = str(Path(__file__).with_name("alembic.ini"))

file_config_path = Path(config.config_file_name)
if file_config_path.exists():
    fileConfig(str(file_config_path))


def get_engine():
    try:
        return current_app.extensions["migrate"].db.get_engine()
    except AttributeError:
        return current_app.extensions["migrate"].db.engine


def get_engine_url() -> str:
    return str(get_engine().url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())
target_metadata = current_app.extensions["migrate"].db.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
