# Testing

JuntosHQ uses [pytest](https://pytest.org/). All tests are in the `tests/` directory and run against an in-memory SQLite database — no PostgreSQL or real OAuth credentials are needed.

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Verbose output (test names + pass/fail)
uv run pytest -v

# Run a single file
uv run pytest tests/test_auth.py -v

# Run a single test by name
uv run pytest tests/test_auth.py::test_non_owner_cannot_edit_junto -v

# Stop on first failure
uv run pytest -x
```

---

## Test Files

| File | What it tests |
|---|---|
| [tests/test_app.py](../tests/test_app.py) | Homepage and About page rendering |
| [tests/test_juntos.py](../tests/test_juntos.py) | Full junto CRUD — forms, create, show, edit, delete |
| [tests/test_members.py](../tests/test_members.py) | Full member CRUD — forms, create, edit, delete, cascade |
| [tests/test_auth.py](../tests/test_auth.py) | Authentication redirects and ownership enforcement |

---

## Fixtures

Defined in [tests/conftest.py](../tests/conftest.py). All fixtures are function-scoped unless noted.

### `app`

Creates a Flask application using `TestConfig`:
- In-memory SQLite (`sqlite://`)
- `TESTING = True`
- Dummy OAuth credentials

```python
@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    yield app
```

### `client`

A Flask test client for making HTTP requests without a running server.

```python
@pytest.fixture
def client(app):
    return app.test_client()
```

### `db`

The SQLAlchemy `db` object within the app context. Use this to add model objects directly in tests.

```python
@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
```

### `user`

A pre-created test `User` in the database.

```python
@pytest.fixture
def user(db):
    u = User(
        provider="github",
        provider_id="test-123",
        email="test@example.com",
        name="Test User",
    )
    db.session.add(u)
    db.session.commit()
    return u
```

### `logged_in_client`

A test client with a valid session already set (bypasses OAuth):

```python
@pytest.fixture
def logged_in_client(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
    return client
```

Use `logged_in_client` when testing routes that require authentication. Use `client` when testing that unauthenticated requests are correctly rejected.

---

## Test Patterns

### Testing unauthenticated access

```python
def test_unauthenticated_create_redirects_to_login(client):
    response = client.post("/juntos/", data={"name": "X"})
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
```

### Testing authenticated access (owner)

```python
def test_owner_can_edit_junto(logged_in_client, db, user):
    junto = Junto(name="Mine", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/edit")
    assert response.status_code == 200
```

### Testing non-owner gets 403

```python
def test_non_owner_cannot_edit_junto(client, db):
    owner = User(provider="google", provider_id="owner-1", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Theirs", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = User(provider="google", provider_id="intruder-2", name="Intruder")
    db.session.add(intruder)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.get(f"/juntos/{junto.id}/edit")
    assert response.status_code == 403
```

### Testing form validation

```python
def test_create_junto_missing_name(logged_in_client):
    response = logged_in_client.post("/juntos/", data={"name": ""})
    assert response.status_code == 200          # re-renders form
    assert b"required" in response.data.lower() # or check flash message
```

### Testing database state after an action

```python
def test_delete_junto(logged_in_client, db, user):
    junto = Junto(name="Mine", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()
    junto_id = junto.id

    response = logged_in_client.post(f"/juntos/{junto_id}/delete")
    assert response.status_code == 302
    assert db.session.get(Junto, junto_id) is None   # gone from DB
```

### Testing cascade delete

```python
def test_cascade_delete_removes_members(logged_in_client, db, user):
    junto = Junto(name="Mine", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    member = Member(name="Alice", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()
    member_id = member.id

    logged_in_client.post(f"/juntos/{junto.id}/delete")
    assert db.session.get(Member, member_id) is None
```

---

## Test Coverage by Area

### `test_app.py`

| Test | Verifies |
|---|---|
| `test_index_empty` | Homepage renders with empty state when no juntos exist |
| `test_about` | About page renders with Franklin-related content |
| `test_index_with_junto` | Homepage shows junto name when one exists |

### `test_juntos.py`

| Test | Verifies |
|---|---|
| `test_new_junto_form` | Authenticated user sees the create form |
| `test_new_junto_form_requires_login` | Unauthenticated → redirect to login |
| `test_create_junto` | POST creates a junto and sets `owner_id` |
| `test_create_junto_missing_name` | Validation: empty name re-renders form |
| `test_show_junto` | Detail page shows junto name and members |
| `test_show_junto_not_found` | 404 for nonexistent junto |
| `test_edit_junto_form` | Owner sees pre-populated edit form |
| `test_update_junto` | Owner can update name and description |
| `test_update_junto_missing_name` | Validation: empty name re-renders form |
| `test_delete_junto` | Owner can delete; junto removed from DB |

### `test_members.py`

| Test | Verifies |
|---|---|
| `test_new_member_form` | Owner sees add-member form |
| `test_create_member` | POST creates member associated with junto |
| `test_create_member_missing_name` | Validation: empty name re-renders form |
| `test_edit_member_form` | Owner sees pre-populated edit form |
| `test_update_member` | Owner can update name and role |
| `test_update_member_missing_name` | Validation: empty name re-renders form |
| `test_delete_member` | Owner can delete member |
| `test_cascade_delete_removes_members` | Deleting junto removes all members |

### `test_auth.py`

| Test | Verifies |
|---|---|
| `test_login_page` | Login page renders with "Sign In" |
| `test_logout_clears_session` | Logout redirects; protected routes now redirect to login |
| `test_unauthenticated_create_redirects_to_login` | POST without session → 302 to login |
| `test_unauthenticated_get_new_redirects_to_login` | GET without session → 302 to login |
| `test_non_owner_cannot_edit_junto` | Non-owner GET edit → 403 |
| `test_non_owner_cannot_delete_junto` | Non-owner POST delete → 403 |
| `test_non_owner_cannot_add_member` | Non-owner POST member create → 403 |
| `test_owner_can_edit_junto` | Owner GET edit → 200 |
| `test_owner_can_delete_junto` | Owner POST delete → 302, junto removed |
| `test_owner_can_add_member` | Owner POST member create → 302 |

---

## Configuration for Tests

`pyproject.toml` specifies:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

Pytest discovers test files automatically within the `tests/` directory. No additional configuration is needed.

---

## Why No OAuth in Tests

OAuth involves external HTTP calls (to Google/GitHub servers) that would make tests slow, flaky, and dependent on network access. The `logged_in_client` fixture bypasses OAuth entirely by writing directly to the test session dictionary — the same mechanism that `load_current_user()` reads on every request.

This approach tests the authorization logic (is `session["user_id"]` set and does it match the owner?) without coupling the tests to the OAuth flow itself. The OAuth callback is covered separately by end-to-end or integration tests (not included in this repository).
