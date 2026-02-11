import pytest

from juntos import create_app
from juntos.config import TestConfig
from juntos.models import User, db as _db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db


@pytest.fixture
def user(db):
    u = User(
        provider="github",
        provider_id="test-user-123",
        email="testuser@example.com",
        name="Test User",
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def logged_in_client(client, user):
    """Test client with session["user_id"] already set, bypassing OAuth."""
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
    return client
