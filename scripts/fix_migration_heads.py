"""Fix the 'Multiple head revisions' Alembic error.

Background
----------
If a previous (now-removed) migration file was applied to the database during
development, the ``alembic_version`` table can end up with two rows instead of
one.  Running ``alembic upgrade head`` then fails with:

    ERROR  Multiple head revisions are present for given argument 'head'; please
           specify a specific target revision …

This script detects that situation and resolves it by:
  1. Printing the current rows in ``alembic_version``.
  2. Keeping only the *known-good* revision (the latest stripe-fields migration,
     ``e2f3a4b5c6d7``), and deleting any other stale rows.
  3. Stamping the database so Alembic agrees about the current revision.

After running this script you should be able to run::

    uv run alembic upgrade head

and the coupon-gating migration (``f0a1b2c3d4e5``) will be applied cleanly.

Usage
-----
    uv run python scripts/fix_migration_heads.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import 'juntos'.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from alembic import command  # noqa: E402
from juntos.config import Config as AppConfig  # noqa: E402

# ── Revision constants ────────────────────────────────────────────────────────
# The last known-good revision *before* the coupon-gating migration.
GOOD_REVISION = "e2f3a4b5c6d7"

# ── Connect ───────────────────────────────────────────────────────────────────
db_url = AppConfig.SQLALCHEMY_DATABASE_URI
if not db_url or not isinstance(db_url, str):
    print(
        "DATABASE_URL is not set. "
        "Set the DATABASE_URL environment variable and retry."
    )
    sys.exit(1)

if db_url.startswith("sqlite"):
    print("This script is intended for PostgreSQL databases only.")
    sys.exit(0)

engine = create_engine(db_url)

with engine.connect() as conn:
    # Check whether the alembic_version table exists at all.
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_name = 'alembic_version'"
            ")"
        )
    )
    table_exists = result.scalar()
    if not table_exists:
        print("alembic_version table does not exist – nothing to fix.")
        sys.exit(0)

    rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    current_versions = [r[0] for r in rows]

print(f"Current alembic_version rows: {current_versions}")

if len(current_versions) <= 1:
    print("Only one (or zero) revision tracked – no fix needed.")
    print("Run:  uv run alembic upgrade head")
    sys.exit(0)

# ── Multiple heads detected ───────────────────────────────────────────────────
print(f"\nMultiple heads detected: {current_versions}")
stale = [v for v in current_versions if v != GOOD_REVISION]

if GOOD_REVISION not in current_versions:
    print(
        f"\nWARNING: The known-good revision '{GOOD_REVISION}' is NOT in the current "
        "alembic_version rows. This script assumes that revision is already applied.\n"
        "If it is not, stamping to it could mark unapplied migrations as complete.\n"
        "Please review your database state manually before proceeding."
    )
    confirm = input("Stamp anyway? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(1)

print(f"Stale / unrecognised revisions that will be removed: {stale}")

confirm = input("\nProceed? This will delete the stale row(s) and re-stamp "
               f"the database to '{GOOD_REVISION}'. [y/N] ").strip().lower()
if confirm != "y":
    print("Aborted.")
    sys.exit(1)

with engine.connect() as conn:
    with conn.begin():
        conn.execute(text("DELETE FROM alembic_version"))

# Use alembic's stamp command so the version table is set correctly.
alembic_cfg = Config(
    str(Path(__file__).resolve().parents[1] / "alembic.ini")
)
command.stamp(alembic_cfg, GOOD_REVISION)
print(f"\nDatabase stamped to revision '{GOOD_REVISION}'.")
print("\nNow run:  uv run alembic upgrade head")
