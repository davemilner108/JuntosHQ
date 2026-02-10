from juntos.models import Junto, Member


def _create_junto(db):
    junto = Junto(name="Test Junto", description="For member tests")
    db.session.add(junto)
    db.session.commit()
    return junto


def test_new_member_form(client, db):
    junto = _create_junto(db)
    response = client.get(f"/juntos/{junto.id}/members/new")
    assert response.status_code == 200
    assert b"Add Member" in response.data


def test_create_member(client, db):
    junto = _create_junto(db)
    response = client.post(
        f"/juntos/{junto.id}/members/",
        data={"name": "Alice", "role": "Leader"},
    )
    assert response.status_code == 302

    member = db.session.execute(db.select(Member)).scalar_one()
    assert member.name == "Alice"
    assert member.role == "Leader"
    assert member.junto_id == junto.id


def test_create_member_missing_name(client, db):
    junto = _create_junto(db)
    response = client.post(
        f"/juntos/{junto.id}/members/", data={"name": "", "role": "Ghost"}
    )
    assert response.status_code == 302
    assert db.session.execute(db.select(Member)).scalar_one_or_none() is None


def test_edit_member_form(client, db):
    junto = _create_junto(db)
    member = Member(name="Bob", role="Scribe", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    response = client.get(f"/juntos/{junto.id}/members/{member.id}/edit")
    assert response.status_code == 200
    assert b"Bob" in response.data


def test_update_member(client, db):
    junto = _create_junto(db)
    member = Member(name="Old", role="Old Role", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    response = client.post(
        f"/juntos/{junto.id}/members/{member.id}/edit",
        data={"name": "New", "role": "New Role"},
    )
    assert response.status_code == 302

    db.session.refresh(member)
    assert member.name == "New"
    assert member.role == "New Role"


def test_update_member_missing_name(client, db):
    junto = _create_junto(db)
    member = Member(name="Keep", role="Role", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    response = client.post(
        f"/juntos/{junto.id}/members/{member.id}/edit",
        data={"name": "", "role": "Role"},
    )
    assert response.status_code == 302

    db.session.refresh(member)
    assert member.name == "Keep"


def test_delete_member(client, db):
    junto = _create_junto(db)
    member = Member(name="Gone", role="Bye", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    response = client.post(f"/juntos/{junto.id}/members/{member.id}/delete")
    assert response.status_code == 302
    assert db.session.execute(db.select(Member)).scalar_one_or_none() is None


def test_cascade_delete_removes_members(client, db):
    junto = _create_junto(db)
    member = Member(name="Cascade", role="Test", junto_id=junto.id)
    db.session.add(member)
    db.session.commit()

    db.session.delete(junto)
    db.session.commit()
    assert db.session.execute(db.select(Member)).scalar_one_or_none() is None
