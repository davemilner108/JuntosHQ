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

    # Optional SMTP config — invite emails only sent if MAIL_SERVER is set
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "noreply@juntoshq.com"
    )

    # Stripe billing
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_STANDARD = os.environ.get("STRIPE_PRICE_STANDARD", "")
    STRIPE_PRICE_EXPANDED = os.environ.get("STRIPE_PRICE_EXPANDED", "")
    STRIPE_PRICE_CHATBOT = os.environ.get("STRIPE_PRICE_CHATBOT", "")

    @property
    def MAIL_ENABLED(self):
        return bool(self.MAIL_SERVER)


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    GOOGLE_CLIENT_ID = "test-google-client-id"
    GOOGLE_CLIENT_SECRET = "test-google-client-secret"
    GITHUB_CLIENT_ID = "test-github-client-id"
    GITHUB_CLIENT_SECRET = "test-github-client-secret"
    MAIL_SUPPRESS_SEND = True
