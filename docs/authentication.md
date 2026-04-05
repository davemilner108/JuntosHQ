# Authentication

JuntosHQ uses **OAuth 2.0** for authentication. No passwords are stored. Users sign in via Google; the app receives a verified identity token from the provider and creates or updates a `User` record.

The OAuth library is [Authlib](https://authlib.org/) (`authlib.integrations.flask_client`). Session state is a standard Flask signed cookie.

---

## Flow Overview

```
User clicks "Sign in with Google"
        │
        ▼
GET /auth/login/google
        │  oauth.google.authorize_redirect(callback_url)
        ▼
Redirect → Google OAuth consent screen
        │  user approves
        ▼
GET /auth/callback/google?code=...&state=...
        │  oauth.google.authorize_access_token()
        │  _parse_google(token)  → {provider_id, email, name, avatar_url}
        │  SELECT user WHERE provider='google' AND provider_id=...
        │  INSERT or UPDATE user record
        │  session["user_id"] = user.id
        ▼
Redirect → homepage
```

---

## Routes

All auth routes live in [src/juntos/routes/auth.py](../src/juntos/routes/auth.py) under the `auth` blueprint (`/auth` prefix).

### `GET /auth/login`

Renders the login page (`auth/login.html`) with a button for Google sign-in.

### `GET /auth/login/<provider>`

Initiates the OAuth redirect. `provider` must be `"google"`. If the user is already signed in (`g.current_user` is set), they are redirected to the homepage instead.

The callback URL passed to the provider is:
```
http://<host>/auth/callback/<provider>
```

### `GET /auth/callback/<provider>`

Handles the provider's redirect after the user approves (or denies) the OAuth request.

**On success:**
1. Exchanges the authorization code for an access token via `authorize_access_token()`.
2. Extracts user profile data using `_parse_google()`.
3. Looks up an existing `User` by `(provider, provider_id)`.
4. Creates a new `User` if none exists; always updates `email`, `name`, `avatar_url` from the latest token.
5. Commits the database transaction.
6. Sets `session["user_id"] = user.id` and marks the session as permanent (7-day lifetime).
7. Flashes a welcome message and redirects to the homepage.

**On failure** (network error, invalid state, user denied):
- Flashes an error message and redirects to `/auth/login`.

### `POST /auth/logout`

Clears the entire session (`session.clear()`), flashes a sign-out confirmation, and redirects to the homepage. Uses `POST` to prevent logout via a link (CSRF consideration).

---

## User Record Lifecycle

```
First sign-in:
  → User does not exist → INSERT new User row → session["user_id"] set

Subsequent sign-ins (same provider):
  → User found by (provider, provider_id) → UPDATE name/email/avatar → session["user_id"] set
```

The unique constraint `uq_user_provider` on `(provider, provider_id)` guarantees that a given provider identity maps to exactly one `User` row.

---

## Session Management

After a successful login:

```python
session["user_id"] = user.id
session.permanent = True   # respects PERMANENT_SESSION_LIFETIME
```

`PERMANENT_SESSION_LIFETIME` is 7 days (configured in `Config`). After this period the cookie expires and the user must sign in again.

On every request, `load_current_user()` (registered as a `before_request` hook) reads `session["user_id"]` and populates `g.current_user`:

```python
g.current_user = db.session.get(User, user_id)
```

If the user record no longer exists in the database (e.g. deleted), the stale `user_id` is removed from the session and `g.current_user` is set to `None`.

---

## OAuth Client Registration

The Authlib client is registered in `create_app()` inside [src/juntos/__init__.py](../src/juntos/__init__.py):

```python
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

**Google** uses the OIDC discovery endpoint (`server_metadata_url`) — Authlib fetches the provider metadata automatically and the `userinfo` claim is embedded in the token response.

Authlib reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` directly from the Flask app config (set via environment variables).

---

## Provider-Specific User Data Parsing

### Google — `_parse_google(token)`

Google's OpenID Connect token includes a `userinfo` claim:

```python
u = token.get("userinfo", {})
return {
    "provider_id": str(u["sub"]),        # stable Google user ID
    "email":       u.get("email"),
    "name":        u.get("name"),
    "avatar_url":  u.get("picture"),
}
```

---

## Testing Without OAuth

Tests bypass OAuth entirely. The `logged_in_client` fixture in `tests/conftest.py` directly writes a `user_id` to the test session:

```python
@pytest.fixture
def logged_in_client(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
    return client
```

No HTTP calls to Google are made in tests. See [Testing](testing.md) for details.
