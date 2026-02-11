from logging.config import fileConfig

from dotenv import load_dotenv

load_dotenv()  # must run before juntos.config is imported

from alembic import context
from sqlalchemy import create_engine, pool

from juntos.config import Config
import juntos.models  # registers all model classes with db.metadata
from juntos.models import db

# Use Config.SQLALCHEMY_DATABASE_URI as a plain Python string.
# Do NOT pass it through config.set_main_option() — Alembic's config parser
# treats % as an interpolation prefix, which breaks URL-encoded passwords
# like %24 (for $), %40 (for @), etc.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=Config.SQLALCHEMY_DATABASE_URI,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, poolclass=pool.NullPool)
    with engine.connect() as connection:
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
