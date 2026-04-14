from juntos.models import Junto, SubscriptionTier


def test_index_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sign in to get started" in response.data


def test_about(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"About JuntosHQ" in response.data
    assert b"Franklin" in response.data


def test_index_with_junto(client, db):
    junto = Junto(name="Test Group", description="A test junto")
    db.session.add(junto)
    db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Group" in response.data


def test_index_shows_create_button_when_under_limit(logged_in_client):
    response = logged_in_client.get("/")
    assert response.status_code == 200
    assert b"Start your Junto" in response.data


def test_index_shows_upgrade_prompt_when_at_limit(logged_in_client, db, user):
    """When a free user owns their maximum number of juntos, show the upgrade prompt."""
    junto = Junto(name="My Junto", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get("/")
    assert response.status_code == 200
    assert b"Create Junto" not in response.data
    assert b"See plans" in response.data


def test_index_shows_create_button_standard_user_under_limit(logged_in_client, db, user):
    """A Standard user with fewer than 3 juntos still sees the Create button."""
    user.subscription_tier = SubscriptionTier.STANDARD
    db.session.commit()

    junto = Junto(name="My Junto", owner_id=user.id)
    db.session.add(junto)
    db.session.commit()

    response = logged_in_client.get("/")
    assert response.status_code == 200
    assert b"New Junto" in response.data
