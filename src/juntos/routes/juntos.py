from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from juntos.auth_utils import login_required, require_junto_owner
from juntos.franklin import get_weekly_prompt
from juntos.models import Commitment, CommitmentStatus, Junto, db

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
    prompt = get_weekly_prompt()
    current_week = prompt["week"]

    commitments_list = Commitment.query.filter(
        Commitment.member_id.in_([m.id for m in junto.members]),
        Commitment.cycle_week == current_week,
    ).all()
    commitments_by_member = {c.member_id: c for c in commitments_list}

    visible_meetings = junto.meetings[: junto.meeting_limit]

    return render_template(
        "juntos/show.html",
        junto=junto,
        prompt=prompt,
        commitments=commitments_by_member,
        current_week=current_week,
        CommitmentStatus=CommitmentStatus,
        meetings=visible_meetings,
    )


@bp.route("/<int:id>/commitments", methods=["POST"])
@login_required
def update_commitments(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    current_week = get_weekly_prompt()["week"]

    for member in junto.members:
        description = request.form.get(f"commitment_desc_{member.id}", "").strip()
        status_value = request.form.get(f"commitment_status_{member.id}", "")

        if not description:
            existing = Commitment.query.filter_by(
                member_id=member.id, cycle_week=current_week
            ).first()
            if existing:
                db.session.delete(existing)
            continue

        try:
            status = CommitmentStatus(status_value)
        except ValueError:
            status = CommitmentStatus.NOT_STARTED

        commitment = Commitment.query.filter_by(
            member_id=member.id, cycle_week=current_week
        ).first()

        if commitment:
            commitment.description = description
            commitment.status = status
        else:
            commitment = Commitment(
                member_id=member.id,
                cycle_week=current_week,
                description=description,
                status=status,
            )
            db.session.add(commitment)

    db.session.commit()
    flash("Commitments updated.", "success")
    return redirect(url_for("juntos.show", id=junto.id))


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
