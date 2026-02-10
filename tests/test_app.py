from juntos.models import Junto


def test_index_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No juntos yet" in response.data


def test_index_with_junto(client, db):
    junto = Junto(name="Test Group", description="A test junto")
    db.session.add(junto)
    db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Test Group" in response.data
