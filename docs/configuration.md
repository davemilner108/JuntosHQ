# Configuration

The application is configured via environment variables loaded from a `.env` file (using [python-dotenv](https://github.com/theskumar/python-dotenv)). The `.env` file lives at the project root and is **never committed to version control** (it is in `.gitignore`).

Configuration classes are defined in [src/juntos/config.py](../src/juntos/config.py).

---

## Environment Variables

### Required in production

| Variable | Description |
|---|---|
| `DATABASE_URL` | Full PostgreSQL connection URL (see format below) |
| `SECRET_KEY` | Random string used to sign the session cookie — keep this secret |

### Required for OAuth sign-in

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret from Google Cloud Console |
| `GITHUB_CLIENT_ID` | OAuth App client ID from GitHub Developer Settings |
| `GITHUB_CLIENT_SECRET` | OAuth App client secret from GitHub Developer Settings |

### Required for billing (Stripe)

| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret key (`sk_live_...` in production) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_PRICE_STANDARD` | Stripe Price ID for the Standard plan (`price_...`) |
| `STRIPE_PRICE_EXPANDED` | Stripe Price ID for the Expanded plan (`price_...`) |
| `STRIPE_PRICE_CHATBOT` | Stripe Price ID for the Ben's Counsel add-on (`price_...`) |

If Stripe keys are absent, checkout routes show a "billing not yet configured" flash and redirect to pricing — safe for free-only deployments.

### Optional: email (invite links)

| Variable | Description |
|---|---|
| `MAIL_SERVER` | SMTP hostname (e.g. `smtp.sendgrid.net`) |
| `MAIL_PORT` | SMTP port (default `587`) |
| `MAIL_USE_TLS` | `true` or `false` (default `true`) |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password or API key |
| `MAIL_DEFAULT_SENDER` | From address (default `noreply@juntoshq.com`) |

If `MAIL_SERVER` is absent, invite emails are silently skipped — the invite link is still generated and shown in the UI.

---

## DATABASE_URL Format

The variable must be a valid PostgreSQL connection URL:

```
postgresql://user:password@host:port/database
```

### Special characters in passwords

If the password contains characters that have special meaning in a URL (such as `$`, `@`, `:`), use one of these approaches:

**Option A — percent-encode the character (no quotes needed):**

```dotenv
DATABASE_URL=postgresql://myuser:mypass@localhost:5433/juntos
```

`%24` is the URL percent-encoding of `$`.

**Option B — double-quote the entire value and use a backslash escape:**

```dotenv
DATABASE_URL="postgresql://myuser:mypass@localhost:5433/juntos"
```

Inside a double-quoted dotenv value, `\$` is interpreted as a literal `$`.

> Note: In an **unquoted** dotenv value, `\$` is treated as a literal backslash followed by a dollar sign, which would produce the wrong password. Always use option A or option B when the password contains `$`.

### Dialect rewriting

`config.py` contains `_normalize_db_url()` which automatically rewrites the URL to use the psycopg v3 dialect:

| Input prefix | Rewritten to |
|---|---|
| `postgres://` | `postgresql+psycopg://` |
| `postgresql://` | `postgresql+psycopg://` |

This makes the app compatible with URLs from Heroku-style `DATABASE_URL` env vars (which use `postgres://`) and standard PostgreSQL URLs.

---

## Config Class

```python
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'juntos.db'}")
    )
    GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # True in production (HTTPS-only cookies); set SESSION_COOKIE_SECURE=false in .flaskenv for local dev
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
```

**Defaults without a `.env` file:**
- `DATABASE_URL` falls back to `sqlite:///instance/juntos.db` (good for a quick local run without PostgreSQL)
- `SECRET_KEY` falls back to `"dev-secret-change-in-production"` — **never use this in production**
- OAuth secrets default to empty strings

---

## TestConfig Class

Used exclusively by the pytest test suite:

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"      # in-memory, per test session
    GOOGLE_CLIENT_ID     = "test-google-client-id"
    GOOGLE_CLIENT_SECRET = "test-google-client-secret"
```

- `sqlite://` (no path) creates a brand-new in-memory database for each test session. There is no file on disk and no cleanup needed.
- The test OAuth credentials are non-functional strings; tests bypass OAuth entirely via the `logged_in_client` fixture.

---

## How Environment Variables Are Loaded

`python-dotenv`'s `load_dotenv()` is called **before** `juntos.config` is imported in two places:

1. **`src/juntos/cli.py`** — the `uv run juntos` entry point loads dotenv before importing the application factory.
2. **`alembic/env.py`** — the Alembic migration runner loads dotenv before importing `Config`.

This is important because `Config` class attributes are evaluated at **class definition time** (when the module is first imported). If `os.environ` does not already contain `DATABASE_URL` at that point, the SQLite fallback is used.

```python
# cli.py
from dotenv import load_dotenv
load_dotenv()                      # sets os.environ from .env

from juntos import create_app      # now safe to import — Config reads correct env vars
```

---

## SECRET_KEY

The session cookie is signed with `SECRET_KEY`. Changing the key invalidates all existing sessions — every signed-in user will be signed out automatically.

Recommended approach for generating a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

In production this should be a long random string stored in a secrets manager or the deployment platform's environment variable system, not in a committed file.

---

## PERMANENT_SESSION_LIFETIME

Set to 7 days (604,800 seconds). After this period, the session cookie expires and the user must sign in again. Changing this value takes effect immediately for new sign-ins; existing sessions retain their original expiry.
