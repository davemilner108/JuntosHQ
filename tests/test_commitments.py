from juntos.models import Commitment, CommitmentStatus, Junto, Member, User


def _create_junto_with_members(db, user, member_count=2):
    junto = Junto(name="Test Junto", description="For commitment tests", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    members = []
    for i in range(member_count):
        member = Member(name=f"Member {i}", role=f"Role {i}", junto_id=junto.id)
        db.session.add(member)
        members.append(member)
    db.session.commit()
    return junto, members


def test_show_page_includes_commitments_section(logged_in_client, db, user):
    junto, _members = _create_junto_with_members(db, user)
    response = logged_in_client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"Commitments" in response.data


def test_owner_can_save_commitments(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user)

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    response = logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "Read a book",
            f"commitment_status_{members[0].id}": "not_started",
            f"commitment_desc_{members[1].id}": "Write a letter",
            f"commitment_status_{members[1].id}": "in_progress",
        },
    )
    assert response.status_code == 302

    c0 = Commitment.query.filter_by(member_id=members[0].id, cycle_week=week).one()
    assert c0.description == "Read a book"
    assert c0.status == CommitmentStatus.NOT_STARTED

    c1 = Commitment.query.filter_by(member_id=members[1].id, cycle_week=week).one()
    assert c1.description == "Write a letter"
    assert c1.status == CommitmentStatus.IN_PROGRESS


def test_owner_can_update_existing_commitment(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "Original",
            f"commitment_status_{members[0].id}": "not_started",
        },
    )

    logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "Updated",
            f"commitment_status_{members[0].id}": "done",
        },
    )

    commitments = Commitment.query.filter_by(
        member_id=members[0].id, cycle_week=week
    ).all()
    assert len(commitments) == 1
    assert commitments[0].description == "Updated"
    assert commitments[0].status == CommitmentStatus.DONE


def test_empty_description_skips_commitment(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    response = logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "",
            f"commitment_status_{members[0].id}": "not_started",
        },
    )
    assert response.status_code == 302
    assert Commitment.query.count() == 0


def test_clearing_description_deletes_existing_commitment(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "Something",
            f"commitment_status_{members[0].id}": "in_progress",
        },
    )
    assert Commitment.query.count() == 1

    logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "",
            f"commitment_status_{members[0].id}": "not_started",
        },
    )
    assert Commitment.query.count() == 0


def test_invalid_status_defaults_to_not_started(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    logged_in_client.post(
        f"/juntos/{junto.id}/commitments",
        data={
            f"commitment_desc_{members[0].id}": "Test",
            f"commitment_status_{members[0].id}": "garbage_value",
        },
    )

    c = Commitment.query.filter_by(member_id=members[0].id, cycle_week=week).one()
    assert c.status == CommitmentStatus.NOT_STARTED


def test_non_owner_cannot_update_commitments(client, db):
    owner = User(provider="github", provider_id="owner-c1", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Theirs", description="Not yours", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = User(provider="github", provider_id="intruder-c2", name="Intruder")
    db.session.add(intruder)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(f"/juntos/{junto.id}/commitments", data={})
    assert response.status_code == 403


def test_unauthenticated_cannot_update_commitments(client, db):
    junto = Junto(name="Public", description="Desc")
    db.session.add(junto)
    db.session.commit()

    response = client.post(f"/juntos/{junto.id}/commitments", data={})
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_show_page_non_owner_sees_readonly(client, db):
    owner = User(provider="github", provider_id="owner-c3", name="Owner")
    db.session.add(owner)
    db.session.commit()

    junto = Junto(name="Viewable", description="Desc", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    member = Member(name="Alice", role="Thinker", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    c = Commitment(
        member_id=member.id,
        cycle_week=week,
        description="Read Voltaire",
        status=CommitmentStatus.IN_PROGRESS,
    )
    db.session.add(c)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}")
    assert response.status_code == 200
    assert b"Read Voltaire" in response.data
    assert b"Save Commitments" not in response.data


def test_commitment_cascade_on_member_delete(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    c = Commitment(
        member_id=members[0].id,
        cycle_week=week,
        description="Will be gone",
        status=CommitmentStatus.NOT_STARTED,
    )
    db.session.add(c)
    db.session.commit()
    assert Commitment.query.count() == 1

    db.session.delete(members[0])
    db.session.commit()
    assert Commitment.query.count() == 0


def test_commitment_cascade_on_junto_delete(logged_in_client, db, user):
    junto, members = _create_junto_with_members(db, user, member_count=1)

    from juntos.franklin import get_weekly_prompt

    week = get_weekly_prompt()["week"]

    c = Commitment(
        member_id=members[0].id,
        cycle_week=week,
        description="Cascade test",
        status=CommitmentStatus.DONE,
    )
    db.session.add(c)
    db.session.commit()

    db.session.delete(junto)
    db.session.commit()
    assert Commitment.query.count() == 0
    assert Member.query.count() == 0
