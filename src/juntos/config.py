import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'juntos.db'}")
    )
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    GOOGLE_CLIENT_ID = "test-google-client-id"
    GOOGLE_CLIENT_SECRET = "test-google-client-secret"
    GITHUB_CLIENT_ID = "test-github-client-id"
    GITHUB_CLIENT_SECRET = "test-github-client-secret"
