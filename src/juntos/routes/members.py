from flask import Blueprint, flash, redirect, render_template, request, url_for

from juntos.auth_utils import login_required, require_junto_owner
from juntos.models import Junto, Member, db

bp = Blueprint("members", __name__, url_prefix="/juntos/<int:junto_id>/members")


@bp.route("/new")
@login_required
def new(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    if junto.is_full:
        flash(
            f"This junto already has {Junto.MAX_MEMBERS} members — the maximum.",
            "error",
        )
        return redirect(url_for("juntos.show", id=junto.id))
    return render_template("members/new.html", junto=junto)


@bp.route("/", methods=["POST"])
@login_required
def create(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)

    if junto.is_full:
        flash(
            f"This junto already has {Junto.MAX_MEMBERS} members — the maximum.",
            "error",
        )
        return redirect(url_for("juntos.show", id=junto.id))

    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    email = request.form.get("email", "").strip() or None
    occupation = request.form.get("occupation", "").strip() or None
    bio = request.form.get("bio", "").strip() or None

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("members.new", junto_id=junto.id))

    member = Member(
        name=name,
        role=role,
        email=email,
        occupation=occupation,
        bio=bio,
        junto_id=junto.id,
    )
    db.session.add(member)
    db.session.commit()
    flash("Member added.", "success")
    return redirect(url_for("juntos.show", id=junto.id))


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(junto_id, id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    member = db.get_or_404(Member, id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        email = request.form.get("email", "").strip() or None
        occupation = request.form.get("occupation", "").strip() or None
        bio = request.form.get("bio", "").strip() or None

        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("members.edit", junto_id=junto.id, id=member.id))

        member.name = name
        member.role = role
        member.email = email
        member.occupation = occupation
        member.bio = bio
        db.session.commit()
        flash("Member updated.", "success")
        return redirect(url_for("juntos.show", id=junto.id))

    return render_template("members/edit.html", junto=junto, member=member)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(junto_id, id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    member = db.get_or_404(Member, id)
    db.session.delete(member)
    db.session.commit()
    flash("Member deleted.", "success")
    return redirect(url_for("juntos.show", id=junto.id))
