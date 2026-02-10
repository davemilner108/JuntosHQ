import pytest

from juntos import create_app
from juntos.config import TestConfig
from juntos.models import db as _db


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
