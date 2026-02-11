# Architecture

## Overview

JuntosHQ is a server-rendered Flask application. All HTML is generated on the server using Jinja2 templates; there is no frontend JavaScript framework. State is carried in a signed session cookie (Flask's default). The database is PostgreSQL in production and in-memory SQLite during tests.

```
Browser
  │  HTTP request
  ▼
Flask WSGI app  (create_app())
  │
  ├─ before_request: load_current_user()
  │       reads session["user_id"] → g.current_user
  │
  ├─ Route dispatch (Blueprint)
  │       main.py    /
  │       auth.py    /auth/*
  │       juntos.py  /juntos/*
  │       members.py /juntos/<id>/members/*
  │
  ├─ View function
  │       reads/writes via SQLAlchemy (db.session)
  │       returns render_template() or redirect()
  │
  └─ context_processor: inject_current_user()
          makes current_user available in every template
```

---

## Application Factory

`create_app(config_class=Config)` in [src/juntos/__init__.py](../src/juntos/__init__.py) wires everything together:

```
create_app()
  1. Flask(__name__)
  2. app.config.from_object(config_class)
  3. db.init_app(app)               # SQLAlchemy
  4. oauth.init_app(app)            # Authlib
  5. oauth.register("google", ...)
  6. oauth.register("github", ...)
  7. register_blueprint(main.bp)
  8. register_blueprint(auth.bp)
  9. register_blueprint(juntos.bp)
  10. register_blueprint(members.bp)
  11. @before_request: load_current_user
  12. @context_processor: inject_current_user
  13. ensure instance/ directory exists (SQLite only)
  14. db.create_all() (SQLite only — Postgres uses Alembic)
```

The factory pattern lets tests call `create_app(TestConfig)` to get a fully isolated app instance with in-memory SQLite.

---

## Request Lifecycle

Every HTTP request goes through these stages:

### 1. `before_request` — user loading

```python
@app.before_request
def load_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.current_user = None
    else:
        g.current_user = db.session.get(User, user_id)
        if g.current_user is None:
            session.pop("user_id", None)  # stale session
```

`g` is request-scoped. `session` is a signed cookie that persists across requests. Storing only `user_id` in the cookie keeps it small; the full `User` record is fetched fresh on every request.

### 2. Route dispatch

Flask matches the URL to a blueprint view function. Blueprint URL prefixes:

| Blueprint | Prefix |
|---|---|
| `main` | (none) |
| `auth` | `/auth` |
| `juntos` | `/juntos` |
| `members` | `/juntos/<int:junto_id>/members` |

### 3. Authorization checks

Views that require authentication call `@login_required` (a decorator) or `require_junto_owner(junto)` (an inline call). These either redirect to `/auth/login` or abort with `403`. See [Authorization](authorization.md).

### 4. Template rendering / redirect

Views return either:
- `render_template("...", **context)` — HTTP 200 with HTML
- `redirect(url_for("..."))` — HTTP 302

Flash messages are written with `flash()` before redirecting and displayed by `base.html` on the next request.

### 5. Context processor

`inject_current_user()` runs before every template render, injecting `current_user` as a template variable:

```python
@app.context_processor
def inject_current_user():
    return {"current_user": g.get("current_user")}
```

Templates use `{% if current_user %}` to conditionally show owner-only controls.

---

## Blueprint Structure

Each blueprint lives in `src/juntos/routes/` and is a thin layer: validate input, call the model, redirect or render.

```
routes/
├── main.py     — public read-only pages
├── auth.py     — OAuth redirect, callback, logout
├── juntos.py   — CRUD for junto resources
└── members.py  — CRUD for member resources (nested under junto)
```

Blueprint endpoint names follow `<blueprint>.<view_name>`, e.g. `url_for("juntos.show", id=1)`.

---

## Session Strategy

| What | Where | Why |
|---|---|---|
| `user_id` (integer) | `session` cookie | Persists across requests (signed, 7-day lifetime) |
| `g.current_user` | `g` object | Request-scoped `User` ORM object; cheap to reload |
| Flash messages | `session` (transient) | One-time display after redirect |

The session cookie is signed with `SECRET_KEY`. If the key changes, all existing sessions are invalidated.

---

## Database Strategy

- **Development / production**: PostgreSQL, managed by Alembic migrations.
- **Tests**: In-memory SQLite (`sqlite://`), created fresh per test session via `db.create_all()`.
- **SQLAlchemy dialect**: `postgresql+psycopg` (psycopg v3). `_normalize_db_url()` in `config.py` rewrites the URL prefix automatically.

---

## Static Assets

All styling is inline or in `<style>` blocks within `base.html`. There is no build step and no JavaScript bundler. This keeps the project simple and avoids frontend tooling dependencies.

---

## Key Source Files

| File | Responsibility |
|---|---|
| [src/juntos/__init__.py](../src/juntos/__init__.py) | Application factory |
| [src/juntos/config.py](../src/juntos/config.py) | Configuration classes |
| [src/juntos/models.py](../src/juntos/models.py) | ORM models |
| [src/juntos/oauth.py](../src/juntos/oauth.py) | Authlib OAuth instance |
| [src/juntos/auth_utils.py](../src/juntos/auth_utils.py) | `login_required`, `require_junto_owner` |
| [src/juntos/cli.py](../src/juntos/cli.py) | `uv run juntos` entry point |
| [src/juntos/routes/auth.py](../src/juntos/routes/auth.py) | OAuth login/callback/logout |
| [src/juntos/routes/juntos.py](../src/juntos/routes/juntos.py) | Junto CRUD |
| [src/juntos/routes/members.py](../src/juntos/routes/members.py) | Member CRUD |
| [alembic/env.py](../alembic/env.py) | Alembic migration runner |
