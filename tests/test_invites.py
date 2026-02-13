"""Tests for member invite flow and expanded model fields."""

from datetime import UTC

import pytest

from juntos.models import (
    Junto,
    Member,
    MemberInvite,
    MemberStatus,
    User,
    db,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def junto(db, user):
    j = Junto(name="Test Junto", description="A test junto", owner_id=user.id)
    db.session.add(j)
    db.session.commit()
    return j


@pytest.fixture
def member(db, junto):
    m = Member(name="Alice", role="Printer", junto_id=junto.id)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def other_user(db):
    u = User(
        provider="github",
        provider_id="other-user-456",
        email="other@example.com",
        name="Other User",
        avatar_url="https://example.com/avatar.png",
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def invite(db, junto, member):
    inv = MemberInvite(junto_id=junto.id, member_id=member.id)
    db.session.add(inv)
    db.session.commit()
    return inv


# ── Create Invite ─────────────────────────────────────────────────


def test_create_invite_generates_token(logged_in_client, junto, member):
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    inv = MemberInvite.query.filter_by(member_id=member.id).first()
    assert inv is not None
    assert len(inv.token) > 20
    assert inv.accepted_at is None


def test_create_invite_with_email(logged_in_client, junto, member):
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id, "email": "alice@example.com"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    inv = MemberInvite.query.filter_by(member_id=member.id).first()
    assert inv.email == "alice@example.com"
    # Also sets member.email if it was None
    m = db.session.get(Member, member.id)
    assert m.email == "alice@example.com"


def test_create_invite_sets_status_invited(logged_in_client, junto, member):
    logged_in_client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id},
        follow_redirects=True,
    )
    m = db.session.get(Member, member.id)
    assert m.status == MemberStatus.INVITED


def test_create_invite_non_owner_403(client, db, junto, member):
    other = User(provider="github", provider_id="stranger-789")
    db.session.add(other)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = other.id
    resp = client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id},
    )
    assert resp.status_code == 403


def test_create_invite_already_linked_member(
    logged_in_client, db, junto, member, other_user
):
    member.user_id = other_user.id
    db.session.commit()
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already has a linked account" in resp.data


def test_create_invite_wrong_junto(logged_in_client, db, user, member):
    other_junto = Junto(name="Other", owner_id=user.id)
    db.session.add(other_junto)
    db.session.commit()
    resp = logged_in_client.post(
        f"/juntos/{other_junto.id}/invites",
        data={"member_id": member.id},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"does not belong" in resp.data


def test_create_invite_unauthenticated(client, junto, member):
    resp = client.post(
        f"/juntos/{junto.id}/invites",
        data={"member_id": member.id},
    )
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# ── Show Invite ───────────────────────────────────────────────────


def test_show_invite_page(client, invite, junto):
    resp = client.get(f"/invite/{invite.token}")
    assert resp.status_code == 200
    assert junto.name.encode() in resp.data
    assert b"invited to join" in resp.data


def test_show_invite_logged_in_shows_accept(logged_in_client, invite):
    resp = logged_in_client.get(f"/invite/{invite.token}")
    assert resp.status_code == 200
    assert b"Accept Invitation" in resp.data


def test_show_invite_not_logged_in_shows_oauth(client, invite):
    resp = client.get(f"/invite/{invite.token}")
    assert resp.status_code == 200
    assert b"Sign in with Google" in resp.data
    assert b"Sign in with GitHub" in resp.data


def test_show_invite_already_accepted(client, db, invite):
    from datetime import datetime

    invite.accepted_at = datetime.now(UTC)
    db.session.commit()
    resp = client.get(f"/invite/{invite.token}")
    assert resp.status_code == 200
    assert b"already been accepted" in resp.data


def test_show_invite_invalid_token(client):
    resp = client.get("/invite/bogus-token-that-doesnt-exist")
    assert resp.status_code == 404


# ── Accept Invite ─────────────────────────────────────────────────


def test_accept_invite_links_member(
    client, db, invite, member, other_user
):
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.post(
        f"/invite/{invite.token}/accept",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    m = db.session.get(Member, member.id)
    assert m.user_id == other_user.id
    assert m.status == MemberStatus.ACTIVE
    assert m.email == other_user.email
    assert m.avatar_url == other_user.avatar_url


def test_accept_invite_sets_accepted_at(client, db, invite, other_user):
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    client.post(f"/invite/{invite.token}/accept")
    inv = db.session.get(MemberInvite, invite.id)
    assert inv.accepted_at is not None


def test_accept_invite_already_accepted(client, db, invite, other_user):
    from datetime import datetime

    invite.accepted_at = datetime.now(UTC)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = other_user.id
    resp = client.post(
        f"/invite/{invite.token}/accept",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already been accepted" in resp.data


def test_accept_invite_invalid_token(logged_in_client):
    resp = logged_in_client.post("/invite/bogus-token/accept")
    assert resp.status_code == 404


def test_accept_invite_unauthenticated(client, invite):
    resp = client.post(f"/invite/{invite.token}/accept")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


# ── OAuth invite token pass-through ──────────────────────────────


def test_oauth_login_stores_invite_token(client, invite):
    client.get(f"/auth/login/google?invite_token={invite.token}")
    # Should redirect to Google OAuth; session should have token
    with client.session_transaction() as sess:
        assert sess.get("pending_invite_token") == invite.token


# ── Cascade Deletes ───────────────────────────────────────────────


def test_delete_junto_cascades_invites(logged_in_client, db, junto, invite):
    db.session.delete(junto)
    db.session.commit()
    assert MemberInvite.query.count() == 0


def test_delete_member_cascades_invites(logged_in_client, db, member, invite):
    # MemberInvite has member backref; deleting member should cascade
    db.session.delete(member)
    db.session.commit()
    assert MemberInvite.query.count() == 0


# ── Junto meeting_url ────────────────────────────────────────────


def test_create_junto_with_meeting_url(logged_in_client, db):
    resp = logged_in_client.post(
        "/juntos/",
        data={
            "name": "Weekly Junto",
            "description": "A weekly junto",
            "meeting_url": "https://zoom.us/j/123456",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    j = Junto.query.filter_by(name="Weekly Junto").first()
    assert j.meeting_url == "https://zoom.us/j/123456"


def test_edit_junto_meeting_url(logged_in_client, db, junto):
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/edit",
        data={
            "name": junto.name,
            "description": junto.description or "",
            "meeting_url": "https://teams.microsoft.com/l/meetup",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(junto)
    assert junto.meeting_url == "https://teams.microsoft.com/l/meetup"


def test_junto_show_displays_meeting_url(client, db, junto):
    junto.meeting_url = "https://zoom.us/j/999"
    db.session.commit()
    resp = client.get(f"/juntos/{junto.id}")
    assert b"Join Meeting" in resp.data
    assert b"https://zoom.us/j/999" in resp.data


def test_junto_show_hides_meeting_url_when_none(client, junto):
    resp = client.get(f"/juntos/{junto.id}")
    assert b"Join Meeting" not in resp.data


# ── Member new fields ─────────────────────────────────────────────


def test_create_member_with_new_fields(logged_in_client, db, junto):
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/members/",
        data={
            "name": "Bob",
            "role": "Scribe",
            "email": "bob@example.com",
            "occupation": "Printer",
            "bio": "Loves books.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    m = Member.query.filter_by(name="Bob").first()
    assert m.email == "bob@example.com"
    assert m.occupation == "Printer"
    assert m.bio == "Loves books."
    assert m.status == MemberStatus.ACTIVE
    assert m.joined_at is not None


def test_edit_member_new_fields(logged_in_client, db, junto, member):
    resp = logged_in_client.post(
        f"/juntos/{junto.id}/members/{member.id}/edit",
        data={
            "name": "Alice Updated",
            "role": "Philosopher",
            "email": "alice@updated.com",
            "occupation": "Philosopher",
            "bio": "Updated bio.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(member)
    assert member.name == "Alice Updated"
    assert member.email == "alice@updated.com"
    assert member.occupation == "Philosopher"
    assert member.bio == "Updated bio."


def test_create_member_empty_optional_fields(logged_in_client, db, junto):
    logged_in_client.post(
        f"/juntos/{junto.id}/members/",
        data={"name": "Minimal", "role": "", "email": "", "occupation": "", "bio": ""},
        follow_redirects=True,
    )
    m = Member.query.filter_by(name="Minimal").first()
    assert m.email is None
    assert m.occupation is None
    assert m.bio is None


# ── User model new fields ────────────────────────────────────────


def test_user_new_fields_nullable(db, user):
    assert user.user_timezone is None
    assert user.bio is None
    assert user.location is None
    assert user.last_active_at is None
    assert user.notification_prefs is None


def test_last_active_at_updated_on_request(logged_in_client, db, user):
    logged_in_client.get("/")
    db.session.refresh(user)
    assert user.last_active_at is not None


# ── Member status on show page ────────────────────────────────────


def test_show_page_member_status_badge(client, db, junto, member):
    resp = client.get(f"/juntos/{junto.id}")
    assert b"member-status-badge--active" in resp.data


def test_show_page_invited_badge(client, db, junto, member):
    member.status = MemberStatus.INVITED
    db.session.commit()
    resp = client.get(f"/juntos/{junto.id}")
    assert b"member-status-badge--invited" in resp.data


def test_show_page_invite_button_for_unlinked(logged_in_client, junto, member):
    resp = logged_in_client.get(f"/juntos/{junto.id}")
    assert b"Invite" in resp.data


def test_show_page_no_invite_for_linked(
    logged_in_client, db, junto, member, other_user
):
    member.user_id = other_user.id
    db.session.commit()
    resp = logged_in_client.get(f"/juntos/{junto.id}")
    # The invite form should not appear for linked members
    assert b"invite-form" not in resp.data
