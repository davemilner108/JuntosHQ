# Getting Started

## Prerequisites

| Tool | Minimum version | Purpose |
|---|---|---|
| Python | 3.12 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Dependency management and script runner |
| PostgreSQL | 14+ | Production database |

A local PostgreSQL server should be running and accessible. The default configuration expects it on `localhost:5433`. You can use any port — just set `DATABASE_URL` in `.env` accordingly.

---

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd JuntosHQ

# Create the virtual environment and install all dependencies
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, creating `.venv/` with all runtime and dev dependencies pinned to exact versions.

---

## Environment Variables

The app reads secrets and credentials from a `.env` file in the project root. This file is listed in `.gitignore` and is never committed.

Create it:

```bash
cp .env.example .env   # if an example file exists, or create manually
```

Minimal `.env` for local development:

```dotenv
DATABASE_URL="postgresql://myuser:mypassword@localhost:5433/juntos"
SECRET_KEY=some-random-string-at-least-32-chars

# Required for OAuth sign-in (see Authentication docs for how to obtain)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

See [Configuration](configuration.md) for the full list of variables.

---

## Database Setup

The schema is managed by Alembic. Run migrations before starting the app for the first time, and after pulling new migrations from the repository.

```bash
# Apply all pending migrations
uv run alembic upgrade head
```

You should see output like:

```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> bcfd19a7fddb, add_user_table_and_junto_owner
```

If you see `SQLiteImpl` instead of `PostgreSQLImpl`, your `DATABASE_URL` is not being picked up — check that `.env` exists and is correctly formatted.

---

## Running the Development Server

```bash
uv run juntos
```

The app starts in debug mode on `http://localhost:5000`. Flask's reloader will restart the process automatically when source files change.

---

## OAuth Provider Setup

OAuth credentials are required for sign-in to work. You need to register the app with at least one provider.

### Google

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
3. Application type: **Web application**.
4. Add an authorized redirect URI: `http://localhost:5000/auth/callback/google`
5. Copy the **Client ID** and **Client Secret** into `.env`.

### GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers) → **New OAuth App**.
2. Set **Authorization callback URL** to: `http://localhost:5000/auth/callback/github`
3. Copy the **Client ID** and **Client Secret** into `.env`.

---

## Running Tests

Tests use an in-memory SQLite database and do not require PostgreSQL or OAuth credentials.

```bash
uv run pytest
```

For verbose output:

```bash
uv run pytest -v
```

See [Testing](testing.md) for a full breakdown of the test suite.

---

## Project Layout

```
JuntosHQ/
├── src/
│   └── juntos/
│       ├── __init__.py        # Application factory
│       ├── cli.py             # `uv run juntos` entry point
│       ├── config.py          # Config and TestConfig classes
│       ├── models.py          # SQLAlchemy models (User, Junto, Member)
│       ├── oauth.py           # Authlib OAuth client instance
│       ├── auth_utils.py      # login_required, require_junto_owner
│       ├── routes/
│       │   ├── main.py        # / and /about
│       │   ├── auth.py        # /auth/* OAuth routes
│       │   ├── juntos.py      # /juntos/* CRUD
│       │   └── members.py     # /juntos/<id>/members/* CRUD
│       └── templates/
│           ├── base.html
│           ├── index.html
│           ├── about.html
│           ├── auth/login.html
│           ├── juntos/        # new.html, show.html, edit.html
│           └── members/       # new.html, edit.html
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── test_app.py
│   ├── test_juntos.py
│   ├── test_members.py
│   └── test_auth.py
├── alembic/
│   ├── env.py                 # Alembic runtime environment
│   └── versions/              # Migration scripts
├── docs/                      # This documentation
├── pyproject.toml
├── alembic.ini
└── .env                       # Local secrets (not committed)
```
