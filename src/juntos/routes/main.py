from flask import Blueprint, render_template

from juntos.models import Junto

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    juntos = Junto.query.all()
    return render_template("index.html", juntos=juntos)

@bp.route("/pricing")
def pricing():
    return render_template("pricing.html")

@bp.route("/about")
def about():
    return render_template("about.html")
