from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from juntos.auth_utils import login_required, require_junto_owner
from juntos.franklin import get_weekly_prompt
from juntos.models import Commitment, CommitmentStatus, Junto, db

bp = Blueprint("juntos", __name__, url_prefix="/juntos")


def _user_junto_count(user_id: int) -> int:
    """Return the number of juntos owned by the given user (efficient DB count)."""
    return (
        db.session.query(func.count(Junto.id))
        .filter(Junto.owner_id == user_id)
        .scalar()
        or 0
    )


@bp.route("/new")
@login_required
def new():
    user = g.current_user
    count = _user_junto_count(user.id)
    if count >= user.junto_limit:
        flash(
            f"You've reached the {user.subscription_tier.value.title()} tier limit "
            f"({count}/{user.junto_limit} juntos). "
            "Upgrade your plan to create more.",
            "error",
        )
        return redirect(url_for("main.pricing"))
    return render_template("juntos/new.html")


@bp.route("/", methods=["POST"])
@login_required
def create():
    user = g.current_user
    count = _user_junto_count(user.id)
    if count >= user.junto_limit:
        flash(
            f"You've reached the {user.subscription_tier.value.title()} tier limit "
            f"({count}/{user.junto_limit} juntos). "
            "Upgrade your plan to create more.",
            "error",
        )
        return redirect(url_for("main.pricing"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("juntos.new"))

    meeting_url = request.form.get("meeting_url", "").strip() or None
    is_public = request.form.get("is_public") == "1"
    junto = Junto(
        name=name,
        description=description,
        owner_id=g.current_user.id,
        meeting_url=meeting_url,
        is_public=is_public,
    )
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
    commitments_by_member = {}
    for c in commitments_list:
        commitments_by_member.setdefault(c.member_id, []).append(c)

    total_meetings = len(junto.meetings)
    visible_meetings = junto.meetings[: junto.meeting_limit]
    hidden_meeting_count = max(0, total_meetings - junto.meeting_limit)

    return render_template(
        "juntos/show.html",
        junto=junto,
        prompt=prompt,
        commitments=commitments_by_member,
        current_week=current_week,
        meetings=visible_meetings,
        hidden_meeting_count=hidden_meeting_count,
    )


@bp.route("/<int:id>/commitments/edit")
@login_required
def edit_commitments(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)
    prompt = get_weekly_prompt()
    current_week = prompt["week"]
    commitments_list = Commitment.query.filter(
        Commitment.member_id.in_([m.id for m in junto.members]),
        Commitment.cycle_week == current_week,
    ).all()
    commitments_by_member = {}
    for c in commitments_list:
        commitments_by_member.setdefault(c.member_id, []).append(c)
    return render_template(
        "juntos/edit_commitments.html",
        junto=junto,
        commitments=commitments_by_member,
        current_week=current_week,
        CommitmentStatus=CommitmentStatus,
        commitment_limit=junto.commitment_limit,
    )


@bp.route("/<int:id>/commitments", methods=["POST"])
@login_required
def update_commitments(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    current_week = get_weekly_prompt()["week"]

    limit = junto.commitment_limit

    for member in junto.members:
        # Delete existing commitments for this member + week
        Commitment.query.filter_by(
            member_id=member.id, cycle_week=current_week
        ).delete()

        # Recreate from submitted slots (up to limit)
        for slot in range(limit):
            desc = request.form.get(
                f"commitment_desc_{member.id}_{slot}", ""
            ).strip()
            status_value = request.form.get(
                f"commitment_status_{member.id}_{slot}", ""
            )
            if not desc:
                continue

            try:
                status = CommitmentStatus(status_value)
            except ValueError:
                status = CommitmentStatus.NOT_STARTED

            db.session.add(
                Commitment(
                    member_id=member.id,
                    cycle_week=current_week,
                    description=desc,
                    status=status,
                )
            )

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

        meeting_url = request.form.get("meeting_url", "").strip() or None
        is_public = request.form.get("is_public") == "1"
        junto.name = name
        junto.description = description
        junto.meeting_url = meeting_url
        junto.is_public = is_public
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
