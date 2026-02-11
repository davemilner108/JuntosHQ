import functools

from flask import abort, flash, g, redirect, url_for


def login_required(view):
    """Decorator: redirects to login if user is not authenticated."""

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def require_junto_owner(junto):
    """Inline ownership check. Call inside any view that requires ownership.
    Aborts with 403 if the current user is not the junto's owner."""
    if g.current_user is None:
        flash("Please sign in to continue.", "error")
        abort(redirect(url_for("auth.login")))
    if junto.owner_id != g.current_user.id:
        abort(403)
