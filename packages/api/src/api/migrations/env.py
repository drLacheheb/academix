from logging.config import fileConfig

from alembic import context
from api.config import get_database_url
from core.infrastructure.db.models import Base
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides access
# to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", get_database_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "pyformat"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {}
    url = config.get_main_option("sqlalchemy.url") or get_database_url()

    if not url.startswith("sqlite"):
        connect_args = {"options": "-c search_path=public"}

    configuration = config.get_section(config.config_ini_section, {}).copy()
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        if not url.startswith("sqlite"):
            from sqlalchemy import text

            connection.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
            connection.commit()

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
