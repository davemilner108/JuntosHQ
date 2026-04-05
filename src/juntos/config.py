import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_DEFAULT_SECRET_KEY = "dev-secret-change-in-production"


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", _DEFAULT_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'instance' / 'juntos.db'}",
        )
    )
    # Disable prepared statements — required for Supabase PgBouncer
    # (transaction pooler on port 6543 does not support them)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"prepare_threshold": None},
    }
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Secure cookies: True in production (HTTPS), False for local dev
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"

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

    # AI model configuration
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # Beta invite / coupon gating
    INVITE_REQUIRED = os.environ.get("INVITE_REQUIRED", "true").lower() == "true"
    HARD_CODED_COUPON = os.environ.get("HARD_CODED_COUPON", "JUNTOS-BETA-2024")
    COUPONS_PER_USER = int(os.environ.get("COUPONS_PER_USER", "10"))

    @property
    def MAIL_ENABLED(self):
        return bool(self.MAIL_SERVER)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    GOOGLE_CLIENT_ID = "test-google-client-id"
    GOOGLE_CLIENT_SECRET = "test-google-client-secret"
    MAIL_SUPPRESS_SEND = True
    INVITE_REQUIRED = False
    SESSION_COOKIE_SECURE = False
