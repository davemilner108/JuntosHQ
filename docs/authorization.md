# Authorization

JuntosHQ uses a simple **ownership model**: every junto belongs to the user who created it. Only the owner can edit or delete the junto, or manage its members. Anyone — including unauthenticated visitors — can view all juntos and their member lists.

The authorization helpers live in [src/juntos/auth_utils.py](../src/juntos/auth_utils.py).

---

## Access Rules

| Action | Unauthenticated | Authenticated (non-owner) | Owner |
|---|---|---|---|
| View homepage | ✅ | ✅ | ✅ |
| View junto detail | ✅ | ✅ | ✅ |
| Create junto | → login | ✅ | ✅ |
| Edit junto | → login | ❌ 403 | ✅ |
| Delete junto | → login | ❌ 403 | ✅ |
| Add member | → login | ❌ 403 | ✅ |
| Edit member | → login | ❌ 403 | ✅ |
| Delete member | → login | ❌ 403 | ✅ |

**→ login** means an HTTP 302 redirect to `/auth/login`.
**❌ 403** means an HTTP 403 Forbidden response.

---

## `@login_required`

A decorator that guards views requiring authentication. If `g.current_user` is `None` (no session, or session expired), the user is redirected to the login page with a flash message.

```python
import functools
from flask import abort, flash, g, redirect, url_for

def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped
```

### Usage

```python
from juntos.auth_utils import login_required

@bp.route("/new")
@login_required
def new():
    return render_template("juntos/new.html")
```

The decorator wraps the view function so that Flask still sees the correct function name (via `functools.wraps`), preserving the endpoint name and docstring.

---

## `require_junto_owner(junto)`

An inline guard (not a decorator) for views that operate on an existing junto. It checks that `g.current_user` is the owner of the junto. Call it at the start of any view that has already fetched the `Junto` from the database.

```python
def require_junto_owner(junto):
    if g.current_user is None:
        flash("Please sign in to continue.", "error")
        abort(redirect(url_for("auth.login")))
    if junto.owner_id != g.current_user.id:
        abort(403)
```

### Usage

```python
from juntos.auth_utils import login_required, require_junto_owner

@bp.route("/<int:id>/edit")
@login_required
def edit(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)   # aborts with 403 if not owner
    return render_template("juntos/edit.html", junto=junto)
```

Using `@login_required` as the decorator ensures the user is authenticated before the view body runs. `require_junto_owner()` then adds the finer-grained ownership check. This two-step approach gives clean separation between "are you logged in?" and "do you own this?".

---

## Ownership vs. Authentication

Both guards check `g.current_user`, which is populated each request by `load_current_user()` (the `before_request` hook in `__init__.py`). There is no separate "is logged in" session flag — if `g.current_user` is a `User` object the user is authenticated; if it is `None` they are not.

The `owner_id` check in `require_junto_owner()` is an integer comparison:

```python
junto.owner_id != g.current_user.id
```

This is reliable because `owner_id` is set from `g.current_user.id` at creation time:

```python
# routes/juntos.py
junto = Junto(
    name=name,
    description=description,
    owner_id=g.current_user.id,
)
```

---

## Template Conditionals

The UI hides owner-only controls from non-owners using Jinja2 conditionals. This is a UX convenience — the HTTP routes enforce the same rules server-side regardless.

```html
{% if current_user and junto.owner_id == current_user.id %}
    <a href="{{ url_for('juntos.edit', id=junto.id) }}">Edit</a>
    <form method="post" action="{{ url_for('juntos.delete', id=junto.id) }}">
        <button type="submit">Delete</button>
    </form>
{% endif %}
```

`current_user` is injected into every template by the `inject_current_user()` context processor. It is the same `User` object as `g.current_user`.

---

## Adding Authorization to a New Route

To protect a new route:

1. Import the helpers:
   ```python
   from juntos.auth_utils import login_required, require_junto_owner
   ```

2. Add `@login_required` to require any authenticated user:
   ```python
   @bp.route("/something")
   @login_required
   def something():
       ...
   ```

3. If the route operates on a specific junto, add the ownership check:
   ```python
   @bp.route("/<int:id>/something")
   @login_required
   def something(id):
       junto = db.get_or_404(Junto, id)
       require_junto_owner(junto)
       ...
   ```
