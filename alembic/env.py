from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from sqlalchemy import text
import pathlib
import sys

# If the URL references an async dialect (eg. postgresql+asyncpg) we will
# create an async engine and run migrations in an async context. This avoids
# "greenlet_spawn has not been called" errors when alembic tries to connect.
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_URL env var when present
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Ensure project root is on the path so we can import the CIE models
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from preciagro.packages.engines.crop_intelligence.app.db.base import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=config.get_main_option(
        "sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    If the configured URL uses an async dialect (for example postgresql+asyncpg)
    create an async engine and run migrations inside an asyncio event loop
    using a synchronous run_sync wrapper for Alembic's migration context.
    """
    url = config.get_main_option("sqlalchemy.url")
    parsed = make_url(url)

    if parsed.drivername and parsed.drivername.endswith("+asyncpg") or \
       "+asyncpg" in str(parsed):
        # async path
        async_engine = create_async_engine(url, poolclass=pool.NullPool)

        async def do_run():
            async with async_engine.connect() as conn:
                await conn.run_sync(lambda connection: context.configure(connection=connection, target_metadata=target_metadata))
                async with conn.begin():
                    await conn.run_sync(lambda connection: context.run_migrations())

        import asyncio as _asyncio
        _asyncio.run(do_run())
    else:
        # sync path
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(connection=connection,
                              target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
