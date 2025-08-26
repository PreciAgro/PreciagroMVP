from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

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

# add your model's MetaData object here for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = None


def run_migrations_offline():
    context.configure(url=config.get_main_option(
        "sqlalchemy.url"), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
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
