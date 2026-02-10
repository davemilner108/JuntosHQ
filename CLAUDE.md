# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JuntosHQ is a Flask web application implementing a global organizational structure based on Ben Franklin's juntos concept — groups of 12 community members with skin in the game changing the world.

## Tech Stack

- **Python 3.12** with **Flask** web framework
- **Flask-SQLAlchemy** with **SQLite** database
- **uv** for package management
- **pytest** for testing, **ruff** for linting

## Commands

```bash
uv sync                          # Install/update all dependencies
uv run flask run                 # Run dev server (or: uv run juntos)
uv run pytest                    # Run all tests
uv run pytest tests/test_app.py::test_index_empty  # Run a single test
uv run ruff check src/ tests/    # Lint
uv run ruff check --fix src/ tests/  # Lint with auto-fix
```

## Architecture

The app uses the **Flask application factory pattern** with a `src` layout.

```
src/juntos/
├── __init__.py      # create_app() factory — registers blueprints, initializes db
├── config.py        # Config and TestConfig classes (env-var driven)
├── models.py        # SQLAlchemy models (Junto, Member) and shared db instance
├── cli.py           # Entry point for `juntos` console script
├── routes/          # Flask blueprints (one module per blueprint)
│   └── main.py      # Main blueprint — index route
├── templates/       # Jinja2 templates (base.html + page templates)
└── static/          # CSS/JS/images
```

- **App factory**: `create_app()` in `src/juntos/__init__.py` — accepts a config class, initializes extensions, registers blueprints, creates tables.
- **Database**: SQLAlchemy `db` instance lives in `models.py`. All models are defined there. SQLite file goes to `instance/juntos.db`.
- **Routes**: Each blueprint module in `routes/` defines a `bp` and gets registered in the factory.
- **Config**: `Config` reads from env vars (`SECRET_KEY`, `DATABASE_URL`). `TestConfig` uses an in-memory SQLite database.
- **Tests**: `tests/conftest.py` provides `app`, `client`, and `db` fixtures using `TestConfig`.
