import datetime

from juntos.models import (
    Commitment,
    CommitmentStatus,
    Junto,
    Meeting,
    MeetingAttendance,
    Member,
    SubscriptionTier,
)


def test_new_junto_form(logged_in_client):
    response = logged_in_client.get("/juntos/new")
    assert response.status_code == 200
    assert b"New Junto" in response.data


def test_new_junto_form_requires_login(client):
    response = client.get("/juntos/new")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_create_junto(logged_in_client, db, user):
    response = logged_in_client.post(
        "/juntos/", data={"name": "Builders", "description": "We build things"}
    )
    assert response.status_code == 302

    junto = db.session.execute(db.select(Junto)).scalar_one()
    assert junto.name == "Builders"
    assert junto.description == "We build things"
    assert junto.owner_id == user.id


def test_create_junto_missing_name(logged_in_client, db):
    response = logged_in_client.post(
        "/juntos/", data={"name": "", "description": "No name"}
    )
    assert response.status_code == 302
    assert db.session.execute(db.select(Junto)).scalar_one_or_none() is None


def test_show_junto(client, db):
    junto = Junto(name="Readers", description="Book club")
    db.session.add(junto)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"Readers" in response.data
    assert b"Book club" in response.data


def test_show_junto_not_found(client):
    response = client.get("/juntos/999")
    assert response.status_code == 404


def test_edit_junto_form(logged_in_client, db, user):
    junto = Junto(name="Original", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/edit")
    assert response.status_code == 200
    assert b"Original" in response.data


def test_update_junto(logged_in_client, db, user):
    junto = Junto(name="Old Name", description="Old desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.post(
        f"/juntos/{junto.id}/edit",
        data={"name": "New Name", "description": "New desc"},
    )
    assert response.status_code == 302

    db.session.refresh(junto)
    assert junto.name == "New Name"
    assert junto.description == "New desc"


def test_update_junto_missing_name(logged_in_client, db, user):
    junto = Junto(name="Keep Me", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.post(
        f"/juntos/{junto.id}/edit", data={"name": "", "description": "Desc"}
    )
    assert response.status_code == 302

    db.session.refresh(junto)
    assert junto.name == "Keep Me"


def test_delete_junto(logged_in_client, db, user):
    junto = Junto(name="Gone", description="Bye", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.post(f"/juntos/{junto.id}/delete")
    assert response.status_code == 302
    assert db.session.execute(db.select(Junto)).scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


def _make_standard_user(db, user):
    """Upgrade the test user to Standard tier in-place."""
    user.subscription_tier = SubscriptionTier.STANDARD
    db.session.commit()


def test_export_meetings_csv_requires_login(client, db):
    junto = Junto(name="Export Club", description="")
    db.session.add(junto)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}/export/meetings.csv")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_export_meetings_csv_requires_standard_tier(logged_in_client, db, user):
    junto = Junto(name="Export Club", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    # User is FREE by default → redirected to pricing
    response = logged_in_client.get(f"/juntos/{junto.id}/export/meetings.csv")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]


def test_export_meetings_csv_standard_user(logged_in_client, db, user):
    _make_standard_user(db, user)

    junto = Junto(name="CSV Junto", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    member = Member(name="Alice", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    meeting = Meeting(
        junto_id=junto.id,
        held_on=datetime.date(2025, 1, 10),
        notes="Discussed plans",
    )
    db.session.add(meeting)
    db.session.commit()

    attendance = MeetingAttendance(meeting_id=meeting.id, member_id=member.id)
    db.session.add(attendance)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/export/meetings.csv")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    data = response.data.decode()
    assert "Date" in data
    assert "2025-01-10" in data
    assert "Alice" in data
    assert "Discussed plans" in data


def test_export_meetings_pdf_standard_user(logged_in_client, db, user):
    _make_standard_user(db, user)

    junto = Junto(name="PDF Junto", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    meeting = Meeting(
        junto_id=junto.id,
        held_on=datetime.date(2025, 2, 14),
        notes="Notes here",
    )
    db.session.add(meeting)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/export/meetings.pdf")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    # PDF binary must start with the PDF magic bytes
    assert response.data[:4] == b"%PDF"


def test_export_commitments_csv_standard_user(logged_in_client, db, user):
    _make_standard_user(db, user)

    junto = Junto(name="Commit Junto", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    member = Member(name="Bob", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    commitment = Commitment(
        member_id=member.id,
        cycle_week=5,
        description="Read one chapter",
        status=CommitmentStatus.DONE,
    )
    db.session.add(commitment)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/export/commitments.csv")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    data = response.data.decode()
    assert "Member" in data
    assert "Bob" in data
    assert "Read one chapter" in data
    assert "done" in data


def test_export_commitments_csv_requires_standard_tier(logged_in_client, db, user):
    junto = Junto(name="Gated", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/export/commitments.csv")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]


def test_export_meetings_pdf_requires_standard_tier(logged_in_client, db, user):
    junto = Junto(name="Gated PDF", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/export/meetings.pdf")
    assert response.status_code == 302
    assert "/pricing" in response.headers["Location"]
