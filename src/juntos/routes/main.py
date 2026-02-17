from flask import Blueprint, g, render_template
from sqlalchemy import or_

from juntos.models import Junto, Member, db

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
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
    else:
        juntos = Junto.query.filter_by(is_public=True).all()

    return render_template("index.html", juntos=juntos)

@bp.route("/pricing")
def pricing():
    return render_template("pricing.html")

@bp.route("/about")
def about():
    return render_template("about.html")
