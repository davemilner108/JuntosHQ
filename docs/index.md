# JuntosHQ Documentation

JuntosHQ is a Flask web application for creating and managing small groups — called **juntos** — inspired by Benjamin Franklin's original Junto society of 1727. Members gather to share knowledge, debate ideas, and pursue mutual self-improvement.

---

## Contents

| Document | What it covers |
|---|---|
| [Getting Started](getting-started.md) | Prerequisites, installation, running locally |
| [Architecture](architecture.md) | Request lifecycle, file layout, design decisions |
| [Data Models](models.md) | User, Junto, Member — fields, relationships, constraints |
| [Authentication](authentication.md) | OAuth flow (Google & GitHub), session management |
| [Authorization](authorization.md) | Ownership model, decorators, HTTP 403 enforcement |
| [Coupon-Based Invitation](features/coupon-based-invitation.md) | Beta gate: sign up with a coupon, view and share your invite codes |
| [Routes](routes.md) | Every HTTP endpoint — URL, method, auth requirements, behaviour |
| [Configuration](configuration.md) | Environment variables, Config and TestConfig classes |
| [Database & Migrations](database.md) | Alembic workflow, schema overview, adding new migrations |
| [Testing](testing.md) | Running the test suite, fixtures, test structure |
| [Deploying on Google Cloud](deployment-gcp.md) | Cloud Run, App Engine, GKE, Compute Engine — options, quick-start, CI/CD |
| [Production Launch Checklist](production-checklist.md) | Step-by-step checklist: Stripe, OAuth, secrets, database, smoke tests |

---

## Quick Start

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd JuntosHQ

# 2. Install dependencies
uv sync

# 3. Copy and fill in environment variables
cp .env.example .env   # then edit .env with real credentials

# 4. Apply database migrations
uv run alembic upgrade head

# 5. Start the development server
uv run juntos
# → http://localhost:5000
```

---

## Key Concepts

**Junto** — A group of up to twelve people with a shared purpose. Each junto has a name, an optional description, and one owner.

**Owner** — The authenticated user who created a junto. Only the owner can edit or delete the junto, or manage its members.

**Member** — A named participant in a junto, optionally assigned a role (e.g., "Philosopher", "Treasurer").

**OAuth authentication** — Users sign in via Google or GitHub. No passwords are stored. The app records a stable `provider_id` from the OAuth provider alongside optional email and display name.
