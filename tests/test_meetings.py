from datetime import date

from juntos.models import (
    Junto,
    JuntoTier,
    Meeting,
    MeetingAttendance,
    Member,
    User,
)


def _create_junto_with_members(db, user, member_count=3):
    junto = Junto(name="Test Junto", description="For meeting tests", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    members = []
    for i in range(member_count):
        member = Member(name=f"Member {i}", role=f"Role {i}", junto_id=junto.id)
        db.session.add(member)
        members.append(member)
    db.session.commit()
    return junto, members


def _create_meeting(db, junto, members, held_on="2026-02-01", notes="Test notes"):
    meeting = Meeting(
        junto_id=junto.id,
        held_on=date.fromisoformat(held_on),
        notes=notes,
    )
    db.session.add(meeting)
    db.session.flush()
    for m in members:
        db.session.add(MeetingAttendance(meeting_id=meeting.id, member_id=m.id))
    db.session.commit()
    return meeting


# --- CRUD Tests ---


def test_new_meeting_form_requires_login(client, db, user):
    junto, _ = _create_junto_with_members(db, user)
    response = client.get(f"/juntos/{junto.id}/meetings/new")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_new_meeting_form_requires_owner(client, db):
    owner = User(provider="github", provider_id="owner-m1", name="Owner")
    db.session.add(owner)
    db.session.commit()
    junto = Junto(name="Theirs", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    other = User(provider="github", provider_id="other-m2", name="Other")
    db.session.add(other)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = other.id

    response = client.get(f"/juntos/{junto.id}/meetings/new")
    assert response.status_code == 403


def test_new_meeting_form_shows_for_owner(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    response = logged_in_client.get(f"/juntos/{junto.id}/meetings/new")
    assert response.status_code == 200
    assert b"Log a Meeting" in response.data
    for m in members:
        assert m.name.encode() in response.data


def test_create_meeting_with_all_fields(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)

    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={
            "held_on": "2026-02-10",
            "location": "The coffee house",
            "url": "https://teams.microsoft.com/meeting/123",
            "agenda": "# Topic 1\nDiscuss goals",
            "instructions": "Bring your notes",
            "notes": "Great discussion today.",
            "attendees": [str(members[0].id), str(members[1].id)],
        },
    )
    assert response.status_code == 302

    meeting = Meeting.query.filter_by(junto_id=junto.id).one()
    assert meeting.held_on == date(2026, 2, 10)
    assert meeting.location == "The coffee house"
    assert meeting.url == "https://teams.microsoft.com/meeting/123"
    assert meeting.agenda == "# Topic 1\nDiscuss goals"
    assert meeting.instructions == "Bring your notes"
    assert meeting.notes == "Great discussion today."
    assert len(meeting.attendances) == 2


def test_create_meeting_date_required(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)

    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "", "notes": "No date"},
    )
    assert response.status_code == 302
    assert Meeting.query.count() == 0


def test_create_meeting_invalid_date(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)

    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "not-a-date", "notes": "Bad date"},
    )
    assert response.status_code == 302
    assert Meeting.query.count() == 0


def test_create_meeting_ignores_invalid_attendee_ids(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={
            "held_on": "2026-02-10",
            "attendees": [str(members[0].id), "999", "abc"],
        },
    )

    meeting = Meeting.query.one()
    assert len(meeting.attendances) == 1


def test_create_meeting_no_attendees(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)

    logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "2026-02-10", "notes": "Solo review"},
    )

    meeting = Meeting.query.one()
    assert len(meeting.attendances) == 0


def test_create_meeting_empty_optional_fields_are_none(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)

    logged_in_client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "2026-02-10"},
    )

    meeting = Meeting.query.one()
    assert meeting.notes is None
    assert meeting.url is None
    assert meeting.location is None
    assert meeting.agenda is None
    assert meeting.instructions is None


# --- View / Show Tests ---


def test_view_meeting_detail(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = _create_meeting(db, junto, members[:2])

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{meeting.id}"
    )
    assert response.status_code == 200
    assert b"February" in response.data
    assert b"Member 0" in response.data
    assert b"Member 1" in response.data
    assert b"Test notes" in response.data


def test_view_meeting_with_all_fields(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = Meeting(
        junto_id=junto.id,
        held_on=date(2026, 2, 10),
        location="Market Street",
        url="https://zoom.us/j/123",
        agenda="Discuss plans",
        instructions="Read chapter 5",
        notes="Good session",
    )
    db.session.add(meeting)
    db.session.commit()

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{meeting.id}"
    )
    assert response.status_code == 200
    assert b"Market Street" in response.data
    assert b"https://zoom.us/j/123" in response.data
    assert b"Discuss plans" in response.data
    assert b"Read chapter 5" in response.data
    assert b"Good session" in response.data


def test_view_meeting_wrong_junto_returns_404(logged_in_client, db, user):
    junto1, members1 = _create_junto_with_members(db, user)
    junto2 = Junto(name="Other Junto", owner_id=user.id)
    db.session.add(junto2)
    db.session.commit()

    meeting = _create_meeting(db, junto1, members1[:1])

    response = logged_in_client.get(
        f"/juntos/{junto2.id}/meetings/{meeting.id}"
    )
    assert response.status_code == 404


def test_view_meeting_renders_markdown(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = Meeting(
        junto_id=junto.id,
        held_on=date(2026, 2, 10),
        notes="**bold text** and *italic*",
    )
    db.session.add(meeting)
    db.session.commit()

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{meeting.id}"
    )
    assert response.status_code == 200
    assert b"<strong>bold text</strong>" in response.data
    assert b"<em>italic</em>" in response.data


# --- Edit Tests ---


def test_edit_meeting(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = _create_meeting(db, junto, members[:1])

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{meeting.id}/edit"
    )
    assert response.status_code == 200
    assert b"Edit Meeting" in response.data

    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/{meeting.id}/edit",
        data={
            "held_on": "2026-03-01",
            "location": "New location",
            "url": "https://teams.example.com",
            "agenda": "Updated agenda",
            "instructions": "Updated instructions",
            "notes": "Updated notes",
            "attendees": [str(members[0].id), str(members[2].id)],
        },
    )
    assert response.status_code == 302

    db.session.refresh(meeting)
    assert meeting.held_on == date(2026, 3, 1)
    assert meeting.location == "New location"
    assert meeting.url == "https://teams.example.com"
    assert meeting.agenda == "Updated agenda"
    assert meeting.instructions == "Updated instructions"
    assert meeting.notes == "Updated notes"
    attendee_member_ids = {a.member_id for a in meeting.attendances}
    assert attendee_member_ids == {members[0].id, members[2].id}


def test_edit_meeting_date_required(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = _create_meeting(db, junto, members[:1])

    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/{meeting.id}/edit",
        data={"held_on": "", "notes": "No date"},
    )
    assert response.status_code == 302
    db.session.refresh(meeting)
    assert meeting.held_on == date(2026, 2, 1)


# --- Delete Tests ---


def test_delete_meeting(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = _create_meeting(db, junto, members[:1])

    assert Meeting.query.count() == 1
    response = logged_in_client.post(
        f"/juntos/{junto.id}/meetings/{meeting.id}/delete"
    )
    assert response.status_code == 302
    assert Meeting.query.count() == 0
    assert MeetingAttendance.query.count() == 0


# --- Access Control ---


def test_non_owner_cannot_create_meeting(client, db):
    owner = User(provider="github", provider_id="owner-m10", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Theirs", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = User(provider="github", provider_id="intruder-m11", name="Intruder")
    db.session.add(intruder)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "2026-02-10"},
    )
    assert response.status_code == 403


def test_non_owner_cannot_edit_meeting(client, db):
    owner = User(provider="github", provider_id="owner-m12", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Theirs", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    meeting = Meeting(junto_id=junto.id, held_on=date(2026, 2, 1))
    db.session.add(meeting)
    db.session.commit()

    intruder = User(provider="github", provider_id="intruder-m13", name="Intruder")
    db.session.add(intruder)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(
        f"/juntos/{junto.id}/meetings/{meeting.id}/edit",
        data={"held_on": "2026-03-01"},
    )
    assert response.status_code == 403


def test_non_owner_cannot_delete_meeting(client, db):
    owner = User(provider="github", provider_id="owner-m14", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Theirs", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    meeting = Meeting(junto_id=junto.id, held_on=date(2026, 2, 1))
    db.session.add(meeting)
    db.session.commit()

    intruder = User(provider="github", provider_id="intruder-m15", name="Intruder")
    db.session.add(intruder)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(
        f"/juntos/{junto.id}/meetings/{meeting.id}/delete"
    )
    assert response.status_code == 403


def test_non_owner_can_view_meeting(client, db):
    owner = User(provider="github", provider_id="owner-m16", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Viewable", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    meeting = Meeting(
        junto_id=junto.id, held_on=date(2026, 2, 1), notes="Public notes"
    )
    db.session.add(meeting)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}/meetings/{meeting.id}")
    assert response.status_code == 200
    assert b"Public notes" in response.data


def test_unauthenticated_cannot_create_meeting(client, db):
    junto = Junto(name="Public")
    db.session.add(junto)
    db.session.commit()

    response = client.post(
        f"/juntos/{junto.id}/meetings/",
        data={"held_on": "2026-02-10"},
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# --- Freemium Tier Tests ---


def test_free_tier_shows_one_meeting_on_show_page(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    assert junto.tier == JuntoTier.FREE
    assert junto.meeting_limit == 1

    _create_meeting(db, junto, members[:1], held_on="2026-01-01", notes="Old meeting")
    _create_meeting(db, junto, members[:1], held_on="2026-02-01", notes="New meeting")

    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"New meeting" not in response.data  # Notes aren't on summary
    # Only 1 "View" link should be present
    assert response.data.count(b"View") == 1


def test_subscription_tier_shows_three_meetings(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    junto.tier = JuntoTier.SUBSCRIPTION
    db.session.commit()
    assert junto.meeting_limit == 3

    for i in range(5):
        _create_meeting(
            db, junto, members[:1], held_on=f"2026-01-{i + 1:02d}"
        )

    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert response.data.count(b"View") == 3


def test_expanded_tier_shows_five_meetings(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    junto.tier = JuntoTier.EXPANDED
    db.session.commit()
    assert junto.meeting_limit == 5

    for i in range(7):
        _create_meeting(
            db, junto, members[:1], held_on=f"2026-01-{i + 1:02d}"
        )

    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert response.data.count(b"View") == 5


def test_meeting_detail_blocked_beyond_tier_limit(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    assert junto.tier == JuntoTier.FREE

    old_meeting = _create_meeting(
        db, junto, members[:1], held_on="2026-01-01", notes="Old"
    )
    _create_meeting(db, junto, members[:1], held_on="2026-02-01", notes="New")

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{old_meeting.id}"
    )
    assert response.status_code == 403


def test_meeting_detail_allowed_within_tier_limit(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)

    meeting = _create_meeting(
        db, junto, members[:1], held_on="2026-02-01", notes="Visible"
    )

    response = logged_in_client.get(
        f"/juntos/{junto.id}/meetings/{meeting.id}"
    )
    assert response.status_code == 200
    assert b"Visible" in response.data


# --- Cascade Delete Tests ---


def test_meetings_cascade_on_junto_delete(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    _create_meeting(db, junto, members[:2])

    assert Meeting.query.count() == 1
    assert MeetingAttendance.query.count() == 2

    db.session.delete(junto)
    db.session.commit()

    assert Meeting.query.count() == 0
    assert MeetingAttendance.query.count() == 0


def test_attendance_cascade_on_member_delete(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=2)
    _create_meeting(db, junto, members)

    assert MeetingAttendance.query.count() == 2

    db.session.delete(members[0])
    db.session.commit()

    assert MeetingAttendance.query.count() == 1


def test_attendance_cascade_on_meeting_delete(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)
    meeting = _create_meeting(db, junto, members[:2])

    assert MeetingAttendance.query.count() == 2

    db.session.delete(meeting)
    db.session.commit()

    assert MeetingAttendance.query.count() == 0


# --- Show page integration ---


def test_show_page_includes_meetings_section(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)
    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"Meetings" in response.data
    assert b"No meetings logged yet." in response.data


def test_show_page_owner_sees_log_button(logged_in_client, db, user):
    junto, _ = _create_junto_with_members(db, user)
    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert b"Log a Meeting" in response.data


def test_show_page_non_owner_no_log_button(client, db):
    owner = User(provider="github", provider_id="owner-m20", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Viewable", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"Log a Meeting" not in response.data
