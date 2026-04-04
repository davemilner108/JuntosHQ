import csv
import io
import re

from flask import (
    Blueprint,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from fpdf import FPDF
from sqlalchemy import func

from juntos.auth_utils import login_required, require_junto_owner
from juntos.franklin import get_weekly_prompt
from juntos.models import (
    Commitment,
    CommitmentStatus,
    Junto,
    JuntoTier,
    SubscriptionTier,
    db,
)

bp = Blueprint("juntos", __name__, url_prefix="/juntos")

# Map user SubscriptionTier → JuntoTier for new juntos
_SUBSCRIPTION_TO_JUNTO_TIER: dict[SubscriptionTier, JuntoTier] = {
    SubscriptionTier.FREE: JuntoTier.FREE,
    SubscriptionTier.STANDARD: JuntoTier.SUBSCRIPTION,
    SubscriptionTier.EXPANDED: JuntoTier.EXPANDED,
}


def _user_junto_count(user_id: int) -> int:
    """Return the number of juntos owned by the given user (efficient DB count)."""
    return (
        db.session.query(func.count(Junto.id))
        .filter(Junto.owner_id == user_id)
        .scalar()
        or 0
    )


def _commitments_by_member(member_ids: list[int], current_week: int) -> dict[int, list]:
    """Return a member_id → [Commitment] mapping for *current_week*.

    For members who have no commitment entered for the current week, fall back
    to permanent seeded defaults stored at cycle_week=0 so the page always
    shows something meaningful without requiring a weekly re-seed.
    """
    current = Commitment.query.filter(
        Commitment.member_id.in_(member_ids),
        Commitment.cycle_week == current_week,
    ).all()
    result: dict[int, list] = {}
    for c in current:
        result.setdefault(c.member_id, []).append(c)

    # Fall back to week-0 defaults for members without a current-week entry.
    missing = [mid for mid in member_ids if mid not in result]
    if missing:
        for c in Commitment.query.filter(
            Commitment.member_id.in_(missing),
            Commitment.cycle_week == 0,
        ).all():
            result.setdefault(c.member_id, []).append(c)

    return result


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

    # Set the junto's tier to match the owner's current subscription
    junto_tier = _SUBSCRIPTION_TO_JUNTO_TIER.get(user.subscription_tier, JuntoTier.FREE)

    junto = Junto(
        name=name,
        description=description,
        owner_id=g.current_user.id,
        meeting_url=meeting_url,
        is_public=is_public,
        tier=junto_tier,
    )
    db.session.add(junto)
    db.session.commit()
    flash("Junto created.", "success")
    return redirect(url_for("juntos.show", id=junto.id))


@bp.route("/<int:id>")
def show(id):
    junto = db.get_or_404(Junto, id)

    # Access control: private juntos are only visible to the owner and members.
    # Public juntos are visible to everyone (including unauthenticated visitors).
    if not junto.is_public:
        current_user = g.current_user
        if current_user is None:
            flash("Sign in to view this junto.", "error")
            return redirect(url_for("auth.login"))
        is_owner = junto.owner_id == current_user.id
        is_member = any(m.user_id == current_user.id for m in junto.members)
        if not is_owner and not is_member:
            flash("This junto is private.", "error")
            return redirect(url_for("main.index"))

    prompt = get_weekly_prompt()
    current_week = prompt["week"]

    member_ids = [m.id for m in junto.members]
    commitments_by_member = _commitments_by_member(member_ids, current_week)

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
    member_ids = [m.id for m in junto.members]
    commitments_by_member = _commitments_by_member(member_ids, current_week)
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


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

_EXPORT_TIERS = (SubscriptionTier.STANDARD, SubscriptionTier.EXPANDED)


def _can_export(user) -> bool:
    """Return True if the user's subscription tier includes the export feature."""
    return user.subscription_tier in _EXPORT_TIERS


def _safe_filename(name: str) -> str:
    """Sanitise a junto name for use in a Content-Disposition filename."""
    return re.sub(r"[^\w\-]", "_", name)


# ---------------------------------------------------------------------------
# Export routes
# ---------------------------------------------------------------------------


@bp.route("/<int:id>/export/meetings.csv")
@login_required
def export_meetings_csv(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    if not _can_export(g.current_user):
        flash("Exporting data requires a Standard or Expanded plan.", "error")
        return redirect(url_for("main.pricing"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Attendee Count", "Attendee Names", "Notes"])
    for meeting in junto.meetings:
        names = ", ".join(a.member.name for a in meeting.attendances)
        notes = (meeting.notes or "")[:500]
        writer.writerow([
            meeting.held_on.isoformat(),
            len(meeting.attendances),
            names,
            notes,
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    fname = _safe_filename(junto.name)
    response.headers["Content-Disposition"] = (
        f"attachment; filename={fname}-meetings.csv"
    )
    return response


@bp.route("/<int:id>/export/meetings.pdf")
@login_required
def export_meetings_pdf(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    if not _can_export(g.current_user):
        flash("Exporting data requires a Standard or Expanded plan.", "error")
        return redirect(url_for("main.pricing"))

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Meeting Log: {junto.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(4)

    for meeting in junto.meetings:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(
            0, 8,
            meeting.held_on.strftime("%B %d, %Y"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 10)
        names = ", ".join(a.member.name for a in meeting.attendances) or "None"
        pdf.cell(
            0, 6,
            f"Attended ({len(meeting.attendances)}): {names}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        if meeting.notes:
            pdf.multi_cell(0, 6, meeting.notes[:500])
        pdf.ln(4)

    response = make_response(bytes(pdf.output()))
    response.headers["Content-Type"] = "application/pdf"
    fname = _safe_filename(junto.name)
    response.headers["Content-Disposition"] = (
        f"attachment; filename={fname}-meetings.pdf"
    )
    return response


@bp.route("/<int:id>/export/commitments.csv")
@login_required
def export_commitments_csv(id):
    junto = db.get_or_404(Junto, id)
    require_junto_owner(junto)

    if not _can_export(g.current_user):
        flash("Exporting data requires a Standard or Expanded plan.", "error")
        return redirect(url_for("main.pricing"))

    all_commitments = (
        Commitment.query.filter(
            Commitment.member_id.in_([m.id for m in junto.members])
        )
        .order_by(Commitment.cycle_week.asc(), Commitment.member_id.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Member", "Commitment", "Status", "Cycle Week"])
    for c in all_commitments:
        writer.writerow([c.member.name, c.description, c.status.value, c.cycle_week])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    fname = _safe_filename(junto.name)
    response.headers["Content-Disposition"] = (
        f"attachment; filename={fname}-commitments.csv"
    )
    return response
