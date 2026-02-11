# Routes

All HTTP endpoints, their auth requirements, and expected behaviour.

Legend:
- **Auth** — `none` = public; `login` = must be authenticated; `owner` = must be the junto's owner
- **→** — redirects to
- **↩** — re-renders the form

---

## Main (`/`)

Blueprint: `main`
File: [src/juntos/routes/main.py](../src/juntos/routes/main.py)

### `GET /`

Renders the homepage.

| | |
|---|---|
| **Auth** | none |
| **Fetches** | All `Junto` rows |
| **Template** | `index.html` |
| **Context** | `juntos` — list of all juntos |

### `GET /about`

Renders the About page describing Franklin's original Junto.

| | |
|---|---|
| **Auth** | none |
| **Template** | `about.html` |

---

## Auth (`/auth`)

Blueprint: `auth`
File: [src/juntos/routes/auth.py](../src/juntos/routes/auth.py)

### `GET /auth/login`

Renders the login page with "Sign in with Google" and "Sign in with GitHub" buttons.

| | |
|---|---|
| **Auth** | none |
| **Template** | `auth/login.html` |

### `GET /auth/login/<provider>`

Initiates the OAuth authorization flow. `provider` must be `google` or `github`.

| | |
|---|---|
| **Auth** | none (if already logged in → `/`) |
| **Success** | → provider OAuth consent screen |
| **Unknown provider** | flash error → `/auth/login` |

### `GET /auth/callback/<provider>`

Handles the OAuth redirect from the provider. Exchanges the authorization code for a token, resolves or creates the `User` record, and establishes the session.

| | |
|---|---|
| **Auth** | none |
| **Success** | session set → `/` with welcome flash |
| **Error** | flash error → `/auth/login` |

### `POST /auth/logout`

Clears the session and redirects to the homepage.

| | |
|---|---|
| **Auth** | none required |
| **Method** | POST only (prevents logout via crafted link) |
| **Success** | session cleared → `/` with sign-out flash |

---

## Juntos (`/juntos`)

Blueprint: `juntos`
File: [src/juntos/routes/juntos.py](../src/juntos/routes/juntos.py)

### `GET /juntos/new`

Renders the "Create Junto" form.

| | |
|---|---|
| **Auth** | login required |
| **Template** | `juntos/new.html` |

### `POST /juntos/`

Processes the create-junto form submission.

| | |
|---|---|
| **Auth** | login required |
| **Body fields** | `name` (required), `description` (optional) |
| **Validation** | Missing `name` → flash error ↩ `juntos/new.html` |
| **Success** | Creates `Junto(owner_id=g.current_user.id)` → `/juntos/<new_id>` |

### `GET /juntos/<int:id>`

Renders the junto detail page showing all members.

| | |
|---|---|
| **Auth** | none |
| **Fetches** | `Junto` by id (404 if not found) |
| **Template** | `juntos/show.html` |
| **Context** | `junto` — the `Junto` object (members accessible via `junto.members`) |

### `GET /juntos/<int:id>/edit`

Renders the edit-junto form pre-populated with current values.

| | |
|---|---|
| **Auth** | owner required |
| **Fetches** | `Junto` by id (404 if not found) |
| **Template** | `juntos/edit.html` |
| **Context** | `junto` |

### `POST /juntos/<int:id>/edit`

Processes the edit form submission.

| | |
|---|---|
| **Auth** | owner required |
| **Body fields** | `name` (required), `description` (optional) |
| **Validation** | Missing `name` → flash error ↩ `juntos/edit.html` |
| **Success** | Updates `junto.name` and `junto.description` → `/juntos/<id>` |

### `POST /juntos/<int:id>/delete`

Deletes the junto and all its members (via cascade).

| | |
|---|---|
| **Auth** | owner required |
| **Fetches** | `Junto` by id (404 if not found) |
| **Success** | `db.session.delete(junto)` → `/` with confirmation flash |

---

## Members (`/juntos/<junto_id>/members`)

Blueprint: `members`
File: [src/juntos/routes/members.py](../src/juntos/routes/members.py)

All member routes require ownership of the parent junto. The junto is fetched first (404 if not found), then `require_junto_owner(junto)` is called.

### `GET /juntos/<int:junto_id>/members/new`

Renders the "Add Member" form.

| | |
|---|---|
| **Auth** | owner required |
| **Template** | `members/new.html` |
| **Context** | `junto` |

### `POST /juntos/<int:junto_id>/members/`

Processes the add-member form submission.

| | |
|---|---|
| **Auth** | owner required |
| **Body fields** | `name` (required), `role` (optional) |
| **Validation** | Missing `name` → flash error ↩ `members/new.html` |
| **Success** | Creates `Member(junto_id=junto.id)` → `/juntos/<junto_id>` |

### `GET /juntos/<int:junto_id>/members/<int:id>/edit`

Renders the edit-member form pre-populated with current values.

| | |
|---|---|
| **Auth** | owner required |
| **Fetches** | `Junto` (404 if not found), `Member` (404 if not found) |
| **Template** | `members/edit.html` |
| **Context** | `junto`, `member` |

### `POST /juntos/<int:junto_id>/members/<int:id>/edit`

Processes the edit-member form submission.

| | |
|---|---|
| **Auth** | owner required |
| **Body fields** | `name` (required), `role` (optional) |
| **Validation** | Missing `name` → flash error ↩ `members/edit.html` |
| **Success** | Updates `member.name` and `member.role` → `/juntos/<junto_id>` |

### `POST /juntos/<int:junto_id>/members/<int:id>/delete`

Deletes the member.

| | |
|---|---|
| **Auth** | owner required |
| **Fetches** | `Junto` (404 if not found), `Member` (404 if not found) |
| **Success** | `db.session.delete(member)` → `/juntos/<junto_id>` |

---

## Summary Table

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/` | — | Homepage: list all juntos |
| GET | `/about` | — | About page |
| GET | `/auth/login` | — | Login page |
| GET | `/auth/login/<provider>` | — | Start OAuth flow |
| GET | `/auth/callback/<provider>` | — | OAuth callback |
| POST | `/auth/logout` | — | Sign out |
| GET | `/juntos/new` | login | New junto form |
| POST | `/juntos/` | login | Create junto |
| GET | `/juntos/<id>` | — | Junto detail |
| GET | `/juntos/<id>/edit` | owner | Edit junto form |
| POST | `/juntos/<id>/edit` | owner | Update junto |
| POST | `/juntos/<id>/delete` | owner | Delete junto |
| GET | `/juntos/<jid>/members/new` | owner | Add member form |
| POST | `/juntos/<jid>/members/` | owner | Create member |
| GET | `/juntos/<jid>/members/<id>/edit` | owner | Edit member form |
| POST | `/juntos/<jid>/members/<id>/edit` | owner | Update member |
| POST | `/juntos/<jid>/members/<id>/delete` | owner | Delete member |

---

## Notes on Edit vs. PUT/DELETE

HTML forms only support `GET` and `POST`. JuntosHQ uses `POST /juntos/<id>/edit` for updates and `POST /juntos/<id>/delete` for deletions rather than `PUT`/`PATCH`/`DELETE`. This is idiomatic for server-rendered Flask applications.
