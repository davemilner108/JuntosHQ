# Data Models

All models are defined in [src/juntos/models.py](../src/juntos/models.py) using Flask-SQLAlchemy. The `db` object is a `SQLAlchemy()` instance initialised in the application factory via `db.init_app(app)`.

---

## Entity-Relationship Diagram

```
┌──────────────────────────┐
│           User           │
│──────────────────────────│
│ id          INTEGER  PK  │
│ provider    VARCHAR(50)  │
│ provider_id VARCHAR(255) │
│ email       VARCHAR(255) │
│ name        VARCHAR(255) │
│ avatar_url  VARCHAR(2048)│
│ created_at  DATETIME     │
└──────────┬───────────────┘
           │ 1
           │ owns
           │ N
┌──────────▼───────────────┐
│          Junto           │
│──────────────────────────│
│ id          INTEGER  PK  │
│ name        VARCHAR(100) │
│ description TEXT         │
│ owner_id    INTEGER  FK  │──► user.id
└──────────┬───────────────┘
           │ 1
           │ has
           │ N
┌──────────▼───────────────┐
│          Member          │
│──────────────────────────│
│ id          INTEGER  PK  │
│ name        VARCHAR(100) │
│ role        VARCHAR(100) │
│ junto_id    INTEGER  FK  │──► junto.id
└──────────────────────────┘
```

---

## User

Represents an authenticated user who has signed in via an OAuth provider.

```python
class User(db.Model):
    __tablename__ = "user"
```

### Fields

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | No | Auto-incrementing primary key |
| `provider` | VARCHAR(50) | No | OAuth provider identifier: `"google"` or `"github"` |
| `provider_id` | VARCHAR(255) | No | Stable user ID issued by the provider |
| `email` | VARCHAR(255) | Yes | Email address (may be `None` if GitHub user has private email) |
| `name` | VARCHAR(255) | Yes | Display name from the provider profile |
| `avatar_url` | VARCHAR(2048) | Yes | URL of the user's profile picture |
| `created_at` | DATETIME | No | UTC timestamp of first sign-in; defaults to `datetime.now(timezone.utc)` |

### Constraints

- **Primary key**: `id`
- **Unique constraint `uq_user_provider`**: `(provider, provider_id)` — the same person can have separate accounts for Google and GitHub, but cannot have two records for the same provider

### Relationships

```python
juntos = db.relationship("Junto", backref="owner", lazy=True)
```

`user.juntos` returns all `Junto` objects owned by this user.
`junto.owner` returns the `User` object (via backref).

### Notes

- Passwords are never stored. Authentication is entirely delegated to the OAuth provider.
- `provider_id` is the authoritative identity field. Email is informational and may change or be absent.
- On each sign-in the `email`, `name`, and `avatar_url` fields are refreshed from the provider, so profile changes propagate automatically.

---

## Junto

Represents a group — the core resource of the application.

```python
class Junto(db.Model):
    __tablename__ = "junto"
```

### Fields

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | No | Auto-incrementing primary key |
| `name` | VARCHAR(100) | No | Group name, required |
| `description` | TEXT | Yes | Free-form description of the group's purpose |
| `owner_id` | INTEGER | Yes | Foreign key to `user.id` — the user who created the group |

`owner_id` is `nullable=True` in the schema so that existing rows are not broken if a user record is deleted in the future. In practice every junto created through the UI will have an `owner_id`.

### Constraints

- **Primary key**: `id`
- **Foreign key `fk_junto_owner_id_user`**: `owner_id → user.id`

### Relationships

```python
members = db.relationship(
    "Member", backref="junto", lazy=True, cascade="all, delete-orphan"
)
```

`junto.members` returns all `Member` objects in this group.
`member.junto` returns the parent `Junto` (via backref).

The `cascade="all, delete-orphan"` setting means that deleting a `Junto` automatically deletes all its `Member` rows from the database — no manual cleanup required.

---

## Member

Represents a single person within a junto.

```python
class Member(db.Model):
    __tablename__ = "member"
```

### Fields

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | INTEGER | No | Auto-incrementing primary key |
| `name` | VARCHAR(100) | No | Member's name, required |
| `role` | VARCHAR(100) | Yes | Optional label for the member's function (e.g. "Philosopher", "Secretary") |
| `junto_id` | INTEGER | No | Foreign key to `junto.id` |

### Constraints

- **Primary key**: `id`
- **Foreign key `fk_member_junto_id_junto`**: `junto_id → junto.id`

---

## Querying Examples

```python
from juntos.models import db, Junto, Member, User

# Fetch all juntos
juntos = db.session.execute(db.select(Junto)).scalars().all()

# Get a single junto or 404
junto = db.get_or_404(Junto, junto_id)

# Lookup user by provider
user = db.session.execute(
    db.select(User).where(
        User.provider == "google",
        User.provider_id == "12345"
    )
).scalar_one_or_none()

# All members of a junto (via relationship)
members = junto.members
```

---

## Cascade Delete Behaviour

Deleting a `Junto` via `db.session.delete(junto)` will automatically issue `DELETE` statements for all related `Member` rows before deleting the `Junto` row. This is enforced at the SQLAlchemy ORM level by `cascade="all, delete-orphan"`.

The Alembic migration does **not** define a `ON DELETE CASCADE` at the database level — the cascade happens in Python. If rows were deleted by raw SQL outside of SQLAlchemy, orphaned `Member` rows would remain.
