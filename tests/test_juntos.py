from juntos.models import Junto


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
    response = logged_in_client.post("/juntos/", data={"name": "", "description": "No name"})
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
