from flask import Blueprint, flash, g, redirect, render_template, url_for
from sqlalchemy import func, or_

from juntos.models import Junto, Member, db

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    at_junto_limit = False
    if g.current_user:
        participating_ids = (
            db.session.query(Member.junto_id)
            .filter(Member.user_id == g.current_user.id)
            .scalar_subquery()
        )
        juntos = Junto.query.filter(
            or_(
                Junto.is_public.is_(True),
                Junto.owner_id == g.current_user.id,
                Junto.id.in_(participating_ids),
            )
        ).all()
        owned_count = (
            db.session.query(func.count(Junto.id))
            .filter(Junto.owner_id == g.current_user.id)
            .scalar()
            or 0
        )
        at_junto_limit = owned_count >= g.current_user.junto_limit
    else:
        juntos = Junto.query.filter_by(is_public=True).all()
        owned_count = 0

    return render_template(
        "index.html",
        juntos=juntos,
        at_junto_limit=at_junto_limit,
        owned_junto_count=owned_count,
    )

@bp.route("/pricing")
def pricing():
    return render_template("pricing.html")

@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/billing/soon")
def billing_soon():
    flash(
        "Paid subscriptions are not yet available. "
        "You are on the free plan. Billing will be enabled before the public launch.",
        "info",
    )
    return redirect(url_for("main.pricing"))
