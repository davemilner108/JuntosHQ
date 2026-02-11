from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from juntos.auth_utils import login_required, require_junto_owner
from juntos.models import Junto, db
from juntos.franklin import get_weekly_prompt

bp = Blueprint("juntos", __name__, url_prefix="/juntos")


@bp.route("/new")
@login_required
def new():
    return render_template("juntos/new.html")


@bp.route("/", methods=["POST"])
@login_required
def create():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("juntos.new"))

    junto = Junto(name=name, description=description, owner_id=g.current_user.id)
    db.session.add(junto)
    db.session.commit()
    flash("Junto created.", "success")
    return redirect(url_for("juntos.show", id=junto.id))


@bp.route("/<int:id>")
def show(id):
    junto = db.get_or_404(Junto, id)
    return render_template("juntos/show.html", junto=junto, prompt=get_weekly_prompt())


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("juntos.edit", id=junto.id))

        junto.name = name
        junto.description = description
        db.session.commit()
        flash("Junto updated.", "success")
        return redirect(url_for("juntos.show", id=junto.id))

    return render_template("juntos/edit.html", junto=junto)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    db.session.delete(junto)
    db.session.commit()
    flash("Junto deleted.", "success")
    return redirect(url_for("main.index"))
