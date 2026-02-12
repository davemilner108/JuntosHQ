from datetime import date

import mistune
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from markupsafe import Markup

from juntos.auth_utils import login_required, require_junto_owner
from juntos.models import Junto, Meeting, MeetingAttendance, db

bp = Blueprint("meetings", __name__, url_prefix="/juntos/<int:junto_id>/meetings")

_markdown = mistune.create_markdown(escape=True)


def _render_notes(text):
    if not text:
        return ""
    return Markup(_markdown(text))


def _viewable_meeting_ids(junto):
    return {m.id for m in junto.meetings[: junto.meeting_limit]}


@bp.route("/new")
@login_required
def new(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    return render_template(
        "meetings/new.html", junto=junto, today=date.today().isoformat()
    )


@bp.route("/", methods=["POST"])
@login_required
def create(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)

    held_on_str = request.form.get("held_on", "").strip()
    if not held_on_str:
        flash("Date is required.", "error")
        return redirect(url_for("meetings.new", junto_id=junto.id))

    try:
        held_on = date.fromisoformat(held_on_str)
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for("meetings.new", junto_id=junto.id))

    url = request.form.get("url", "").strip()
    location = request.form.get("location", "").strip()
    agenda = request.form.get("agenda", "").strip()
    instructions = request.form.get("instructions", "").strip()
    notes = request.form.get("notes", "").strip()
    attendee_ids = request.form.getlist("attendees")

    meeting = Meeting(
        junto_id=junto.id,
        held_on=held_on,
        url=url or None,
        location=location or None,
        agenda=agenda or None,
        instructions=instructions or None,
        notes=notes or None,
    )
    db.session.add(meeting)
    db.session.flush()

    member_ids = {m.id for m in junto.members}
    for aid in attendee_ids:
        try:
            mid = int(aid)
        except ValueError:
            continue
        if mid in member_ids:
            db.session.add(MeetingAttendance(meeting_id=meeting.id, member_id=mid))

    db.session.commit()
    flash("Meeting logged.", "success")
    return redirect(url_for("juntos.show", id=junto.id))


@bp.route("/<int:id>")
def show(junto_id, id):
    junto = db.get_or_404(Junto, junto_id)
    meeting = db.get_or_404(Meeting, id)

    if meeting.junto_id != junto.id:
        abort(404)

    if meeting.id not in _viewable_meeting_ids(junto):
        abort(403)

    attendee_ids = {a.member_id for a in meeting.attendances}
    return render_template(
        "meetings/show.html",
        junto=junto,
        meeting=meeting,
        attendee_ids=attendee_ids,
        agenda_html=_render_notes(meeting.agenda),
        notes_html=_render_notes(meeting.notes),
    )


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(junto_id, id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    meeting = db.get_or_404(Meeting, id)

    if meeting.junto_id != junto.id:
        abort(404)

    if request.method == "POST":
        held_on_str = request.form.get("held_on", "").strip()
        if not held_on_str:
            flash("Date is required.", "error")
            return redirect(
                url_for("meetings.edit", junto_id=junto.id, id=meeting.id)
            )

        try:
            held_on = date.fromisoformat(held_on_str)
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(
                url_for("meetings.edit", junto_id=junto.id, id=meeting.id)
            )

        url = request.form.get("url", "").strip()
        location = request.form.get("location", "").strip()
        agenda = request.form.get("agenda", "").strip()
        instructions = request.form.get("instructions", "").strip()
        notes = request.form.get("notes", "").strip()
        attendee_ids = request.form.getlist("attendees")

        meeting.held_on = held_on
        meeting.url = url or None
        meeting.location = location or None
        meeting.agenda = agenda or None
        meeting.instructions = instructions or None
        meeting.notes = notes or None

        MeetingAttendance.query.filter_by(meeting_id=meeting.id).delete()

        member_ids = {m.id for m in junto.members}
        for aid in attendee_ids:
            try:
                mid = int(aid)
            except ValueError:
                continue
            if mid in member_ids:
                db.session.add(
                    MeetingAttendance(meeting_id=meeting.id, member_id=mid)
                )

        db.session.commit()
        flash("Meeting updated.", "success")
        return redirect(url_for("juntos.show", id=junto.id))

    attendee_ids = {a.member_id for a in meeting.attendances}
    return render_template(
        "meetings/edit.html",
        junto=junto,
        meeting=meeting,
        attendee_ids=attendee_ids,
    )


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(junto_id, id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)
    meeting = db.get_or_404(Meeting, id)

    if meeting.junto_id != junto.id:
        abort(404)

    db.session.delete(meeting)
    db.session.commit()
    flash("Meeting deleted.", "success")
    return redirect(url_for("juntos.show", id=junto.id))
