from datetime import UTC, datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from juntos.auth_utils import login_required, require_junto_owner
from juntos.models import Junto, Member, MemberInvite, MemberStatus, db

bp = Blueprint("invites", __name__)


@bp.route("/juntos/<int:junto_id>/invites", methods=["POST"])
@login_required
def create(junto_id):
    junto = db.get_or_404(Junto, junto_id)
    require_junto_owner(junto)

    member_id = request.form.get("member_id", type=int)
    email = request.form.get("email", "").strip() or None
    member = db.get_or_404(Member, member_id)

    if member.junto_id != junto.id:
        flash("Member does not belong to this junto.", "error")
        return redirect(url_for("juntos.show", id=junto.id))

    if member.user_id is not None:
        flash(f"{member.name} already has a linked account.", "error")
        return redirect(url_for("juntos.show", id=junto.id))

    invite = MemberInvite(junto_id=junto.id, member_id=member.id, email=email)
    db.session.add(invite)

    if member.user_id is None:
        member.status = MemberStatus.INVITED

    if email and member.email is None:
        member.email = email

    db.session.commit()

    invite_url = url_for("invites.show_invite", token=invite.token, _external=True)

    # Send email if Flask-Mail is configured and email is provided
    mail = current_app.extensions.get("mail")
    if mail and email:
        from flask_mail import Message

        msg = Message(
            subject=f"You're invited to join {junto.name} on JuntosHQ",
            recipients=[email],
            html=render_template(
                "invites/email.html",
                junto=junto,
                member=member,
                invite_url=invite_url,
            ),
        )
        mail.send(msg)
        flash(f"Invite sent to {email}.", "success")
    else:
        flash("Invite link created. Share it with the member.", "success")

    flash(invite_url, "invite_link")
    return redirect(url_for("juntos.show", id=junto.id))


@bp.route("/invite/<token>")
def show_invite(token):
    invite = db.session.execute(
        db.select(MemberInvite).where(MemberInvite.token == token)
    ).scalar_one_or_none()

    if invite is None:
        flash("Invalid or expired invite link.", "error")
        return redirect(url_for("main.index")), 404

    return render_template(
        "invites/show.html",
        invite=invite,
        junto=invite.junto,
        member=invite.member,
        already_accepted=invite.accepted_at is not None,
    )


@bp.route("/invite/<token>/accept", methods=["POST"])
@login_required
def accept_invite(token):
    invite = db.session.execute(
        db.select(MemberInvite).where(MemberInvite.token == token)
    ).scalar_one_or_none()

    if invite is None:
        flash("Invalid or expired invite link.", "error")
        return redirect(url_for("main.index")), 404

    if invite.accepted_at is not None:
        flash("This invitation has already been accepted.", "error")
        return redirect(url_for("juntos.show", id=invite.junto_id))

    member = invite.member
    user = g.current_user

    member.user_id = user.id
    member.status = MemberStatus.ACTIVE
    if not member.email and user.email:
        member.email = user.email
    if not member.avatar_url and user.avatar_url:
        member.avatar_url = user.avatar_url

    invite.accepted_at = datetime.now(UTC)
    db.session.commit()

    flash(f"Welcome to {invite.junto.name}!", "success")
    return redirect(url_for("juntos.show", id=invite.junto_id))
