from juntos.models import Junto


def test_index_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No juntos yet" in response.data


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
