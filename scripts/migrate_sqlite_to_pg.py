"""
One-shot data migration: SQLite -> PostgreSQL.

Usage:
    DATABASE_URL=postgresql+psycopg://user:pass@localhost/juntos \
        uv run python scripts/migrate_sqlite_to_pg.py

Run against an empty PostgreSQL database (after `alembic upgrade head`).
The script will fail loudly on duplicate primary keys, preventing accidental
double-migration.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_URL = f"sqlite:///{BASE_DIR / 'instance' / 'juntos.db'}"
sqlite_engine = create_engine(SQLITE_URL)

pg_url = os.environ["DATABASE_URL"]
if pg_url.startswith("postgres://"):
    pg_url = "postgresql://" + pg_url[len("postgres://"):]
if pg_url.startswith("postgresql://"):
    pg_url = "postgresql+psycopg://" + pg_url[len("postgresql://"):]
pg_engine = create_engine(pg_url)

with sqlite_engine.connect() as src, pg_engine.connect() as dst:
    juntos = src.execute(text("SELECT id, name, description FROM junto")).fetchall()
    print(f"Migrating {len(juntos)} junto rows...")
    for row in juntos:
        dst.execute(
            text("INSERT INTO junto (id, name, description) VALUES (:id, :name, :description)"),
            {"id": row.id, "name": row.name, "description": row.description},
        )

    members = src.execute(text("SELECT id, name, role, junto_id FROM member")).fetchall()
    print(f"Migrating {len(members)} member rows...")
    for row in members:
        dst.execute(
            text("INSERT INTO member (id, name, role, junto_id) VALUES (:id, :name, :role, :junto_id)"),
            {"id": row.id, "name": row.name, "role": row.role, "junto_id": row.junto_id},
        )

    # Reset sequences — required after inserting explicit IDs.
    # Without this the next INSERT would try ID 1 and hit a duplicate key error.
    dst.execute(text("SELECT setval('junto_id_seq', (SELECT MAX(id) FROM junto))"))
    dst.execute(text("SELECT setval('member_id_seq', (SELECT MAX(id) FROM member))"))

    dst.commit()

print("Migration complete.")
