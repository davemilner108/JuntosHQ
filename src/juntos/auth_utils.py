import functools

from flask import abort, current_app, flash, g, redirect, url_for


def login_required(view):
    """Decorator: redirects to login if user is not authenticated.

    Also redirects to the coupon page if the user is signed in but has not
    yet redeemed a signup coupon (when INVITE_REQUIRED is True).
    """

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.login"))
        if (
            current_app.config.get("INVITE_REQUIRED")
            and not g.current_user.signup_verified
        ):
            flash("Please enter your signup coupon to continue.", "info")
            return redirect(url_for("coupons.enter_coupon"))
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
