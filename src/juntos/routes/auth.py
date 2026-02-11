from flask import Blueprint, flash, g, redirect, render_template, session, url_for

from juntos.models import User, db
from juntos.oauth import oauth

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _parse_google(token):
    u = token.get("userinfo", {})
    return {
        "provider_id": str(u["sub"]),
        "email": u.get("email"),
        "name": u.get("name"),
        "avatar_url": u.get("picture"),
    }


def _parse_github(token):
    resp = oauth.github.get("https://api.github.com/user", token=token)
    resp.raise_for_status()
    d = resp.json()
    return {
        "provider_id": str(d["id"]),
        "email": d.get("email"),
        "name": d.get("name") or d.get("login"),
        "avatar_url": d.get("avatar_url"),
    }


_PARSERS = {"google": _parse_google, "github": _parse_github}


@bp.route("/login")
def login():
    return render_template("auth/login.html")


@bp.route("/login/<provider>")
def oauth_login(provider):
    if provider not in _PARSERS:
        flash(f"Unknown provider: {provider}", "error")
        return redirect(url_for("auth.login"))
    if g.current_user:
        return redirect(url_for("main.index"))
    callback = url_for("auth.callback", provider=provider, _external=True)
    return getattr(oauth, provider).authorize_redirect(callback)


@bp.route("/callback/<provider>")
def callback(provider):
    if provider not in _PARSERS:
        flash("Unknown OAuth provider.", "error")
        return redirect(url_for("auth.login"))
    try:
        token = getattr(oauth, provider).authorize_access_token()
    except Exception:
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    info = _PARSERS[provider](token)
    user = db.session.execute(
        db.select(User).where(
            User.provider == provider,
            User.provider_id == info["provider_id"],
        )
    ).scalar_one_or_none()

    if user is None:
        user = User(provider=provider, provider_id=info["provider_id"])
        db.session.add(user)

    user.email = info["email"]
    user.name = info["name"]
    user.avatar_url = info["avatar_url"]
    db.session.commit()

    session["user_id"] = user.id
    session.permanent = True
    flash(f"Welcome, {user.name or 'friend'}!", "success")
    return redirect(url_for("main.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.index"))
