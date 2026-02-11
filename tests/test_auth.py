from juntos.models import Junto, User


def _make_user(db, provider_id, provider="google"):
    u = User(provider=provider, provider_id=provider_id, name=f"User {provider_id}")
    db.session.add(u)
    db.session.commit()
    return u


def test_login_page(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data


def test_logout_clears_session(logged_in_client):
    response = logged_in_client.post("/auth/logout")
    assert response.status_code == 302

    # After logout, a protected route should redirect to login
    response = logged_in_client.get("/juntos/new")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_unauthenticated_create_redirects_to_login(client):
    response = client.post("/juntos/", data={"name": "X"})
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_unauthenticated_get_new_redirects_to_login(client):
    response = client.get("/juntos/new")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_non_owner_cannot_edit_junto(client, db):
    owner = _make_user(db, "owner-1")
    junto = Junto(name="Theirs", description="Not yours", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = _make_user(db, "intruder-2")
    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.get(f"/juntos/{junto.id}/edit")
    assert response.status_code == 403


def test_non_owner_cannot_delete_junto(client, db):
    owner = _make_user(db, "owner-3")
    junto = Junto(name="Protected", description="Stay", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = _make_user(db, "intruder-4")
    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(f"/juntos/{junto.id}/delete")
    assert response.status_code == 403


def test_non_owner_cannot_add_member(client, db):
    owner = _make_user(db, "owner-5")
    junto = Junto(name="Theirs", description="Desc", owner_id=owner.id)
    db.session.add(junto)
    db.session.commit()

    intruder = _make_user(db, "intruder-6")
    with client.session_transaction() as sess:
        sess["user_id"] = intruder.id

    response = client.post(
        f"/juntos/{junto.id}/members/",
        data={"name": "Alice", "role": "Member"},
    )
    assert response.status_code == 403


def test_owner_can_edit_junto(logged_in_client, db, user):
    junto = Junto(name="Mine", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get(f"/juntos/{junto.id}/edit")
    assert response.status_code == 200


def test_owner_can_delete_junto(logged_in_client, db, user):
    junto = Junto(name="Mine", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.post(f"/juntos/{junto.id}/delete")
    assert response.status_code == 302
    assert db.session.get(Junto, junto.id) is None


def test_owner_can_add_member(logged_in_client, db, user):
    junto = Junto(name="Mine", description="Desc", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.post(
        f"/juntos/{junto.id}/members/",
        data={"name": "Alice", "role": "Thinker"},
    )
    assert response.status_code == 302
