# Database & Migrations

JuntosHQ uses **PostgreSQL** in production, managed by [Alembic](https://alembic.sqlalchemy.org/) for schema migrations. During tests an in-memory SQLite database is used instead (no Alembic needed).

---

## Schema Overview

Three tables are created by the initial migration (`bcfd19a7fddb`):

### `user`

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `provider` | VARCHAR(50) | NOT NULL |
| `provider_id` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | |
| `name` | VARCHAR(255) | |
| `avatar_url` | VARCHAR(2048) | |
| `created_at` | DATETIME | NOT NULL |

Unique constraint: `uq_user_provider` on `(provider, provider_id)`.

### `junto`

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `name` | VARCHAR(100) | NOT NULL |
| `description` | TEXT | |
| `owner_id` | INTEGER | FK → `user.id` |

Foreign key constraint: `fk_junto_owner_id_user`.

### `member`

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY |
| `name` | VARCHAR(100) | NOT NULL |
| `role` | VARCHAR(100) | |
| `junto_id` | INTEGER | NOT NULL, FK → `junto.id` |

Foreign key constraint: `fk_member_junto_id_junto`.

---

## Alembic Setup

Configuration is split across two files:

### `alembic.ini`

Standard Alembic config file. The `script_location` points to the `alembic/` directory. **The database URL is not set here** — it would break with URL-encoded passwords. The URL is injected at runtime by `env.py`.

### `alembic/env.py`

The Alembic runtime environment. Key responsibilities:

1. **Loads `.env` before anything else** — `load_dotenv()` runs before `Config` is imported, ensuring `DATABASE_URL` is in `os.environ`.
2. **Imports all models** — `import juntos.models` registers every `db.Model` subclass with `db.metadata`. This is what enables `--autogenerate` to detect schema changes.
3. **Passes the URL directly** — `Config.SQLALCHEMY_DATABASE_URI` is passed to SQLAlchemy without going through Alembic's config parser (which would misinterpret `%` in percent-encoded passwords).

```python
# Key pattern in env.py
from dotenv import load_dotenv
load_dotenv()
from juntos.config import Config
import juntos.models           # registers models with db.metadata
from juntos.models import db

target_metadata = db.metadata
```

---

## Common Alembic Commands

All commands are run with `uv run` to use the project's virtual environment.

### Apply all pending migrations

```bash
uv run alembic upgrade head
```

Run this:
- After cloning the repository for the first time
- After pulling new migration files from the repository

### Check current migration state

```bash
uv run alembic current
```

Shows which revision the database is currently at.

### View migration history

```bash
uv run alembic history --verbose
```

### Roll back one migration

```bash
uv run alembic downgrade -1
```

### Roll back to a specific revision

```bash
uv run alembic downgrade bcfd19a7fddb
```

### Roll back all migrations (empty schema)

```bash
uv run alembic downgrade base
```

---

## Adding a New Migration

When you change a model in `models.py`, generate a migration with `--autogenerate`:

```bash
uv run alembic revision --autogenerate -m "describe_the_change"
```

Alembic compares the current database schema against the SQLAlchemy models and generates a new file in `alembic/versions/`.

**Always review the generated file before applying it.** Alembic's autogenerate cannot detect:
- Renames (it will generate a drop + add)
- Constraint changes on existing columns in some cases
- Data migrations (populating new columns from old ones)

After reviewing:

```bash
uv run alembic upgrade head
```

---

## Migration File Anatomy

Each migration file in `alembic/versions/` follows this structure:

```python
"""describe the change

Revision ID: <hash>
Revises: <parent_hash>
Create Date: YYYY-MM-DD HH:MM:SS
"""
from alembic import op
import sqlalchemy as sa

revision = "<hash>"
down_revision = "<parent_hash>"   # None for the first migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Forward migration — create/alter tables
    ...

def downgrade() -> None:
    # Reverse migration — drop/revert tables
    ...
```

Alembic uses `down_revision` to build the migration chain. Multiple migrations form a linked list from `None` (initial state) to `head`.

---

## Development vs. Production

### Development (SQLite fallback)

If `DATABASE_URL` is not set, the app creates an SQLite database at `instance/juntos.db`. In this mode:

- `db.create_all()` is called in `create_app()` to create tables directly from models (no Alembic).
- This is convenient for quick local runs but means the schema is not tracked by migrations.
- The `instance/` directory is created automatically if it doesn't exist.

### Tests (in-memory SQLite)

`TestConfig` sets `SQLALCHEMY_DATABASE_URI = "sqlite://"`. The `db` fixture in `conftest.py` calls `db.create_all()` within the app context, creating a fresh in-memory database for each test session. There is no `instance/` file created.

### Production (PostgreSQL + Alembic)

Set `DATABASE_URL` in `.env` (or the deployment platform's environment). Run `uv run alembic upgrade head` to apply the schema. The app does **not** call `db.create_all()` for PostgreSQL — schema management is entirely through migrations.

---

## Verifying the Connection

To check that the app can connect to PostgreSQL before running:

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from juntos.config import Config
from sqlalchemy import create_engine, text
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
with engine.connect() as conn:
    print(conn.execute(text('SELECT version()')).scalar())
"
```

A successful output looks like:
```
PostgreSQL 16.2 on x86_64-pc-linux-gnu, ...
```

If you see `password authentication failed`, check that `DATABASE_URL` in `.env` uses the correct password encoding (see [Configuration](configuration.md)).
