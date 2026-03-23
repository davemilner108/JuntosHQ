import logging
import os
import warnings
from datetime import UTC, datetime

from flask import Flask, g, session

from juntos.config import _DEFAULT_SECRET_KEY, Config

logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Warn loudly if the application is running with the default development
    # secret key outside of a testing context.
    if (
        not app.config.get("TESTING")
        and app.config.get("SECRET_KEY") == _DEFAULT_SECRET_KEY
    ):
        warnings.warn(
            "SECRET_KEY is set to the default development value. "
            "Set the SECRET_KEY environment variable to a strong random value "
            "before deploying to production.",
            stacklevel=1,
        )

    from juntos.models import db

    db.init_app(app)

    from juntos.oauth import oauth

    oauth.init_app(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    oauth.register(
        name="github",
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        client_kwargs={"scope": "read:user user:email"},
    )

    # Optional Flask-Mail setup
    if app.config.get("MAIL_SERVER"):
        from flask_mail import Mail

        app.extensions["mail"] = Mail(app)

    from juntos.routes import (
        auth,
        billing,
        chat,
        coupons,
        invites,
        juntos,
        main,
        meetings,
        members,
    )

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(coupons.bp)
    app.register_blueprint(juntos.bp)
    app.register_blueprint(members.bp)
    app.register_blueprint(meetings.bp)
    app.register_blueprint(invites.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(billing.bp)

    @app.cli.command("seed")
    def seed_command():
        """Seed the database with default data."""
        from juntos.seed import run

        run()

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.current_user = None
        else:
            from juntos.models import User

            g.current_user = db.session.get(User, user_id)
            if g.current_user is None:
                session.pop("user_id", None)
            else:
                g.current_user.last_active_at = datetime.now(UTC)
                db.session.commit()

    @app.context_processor
    def inject_current_user():
        return {"current_user": g.get("current_user")}

    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")

    if uri.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(uri[10:]), exist_ok=True)

    with app.app_context():
        if uri.startswith("sqlite"):
            db.create_all()

        # Ensure the Philadelphia Junto and its permanent week-0 seed commitments
        # exist on every startup.  The helper is idempotent — it skips rows that
        # are already present — so this is safe to run repeatedly.
        # Skipped in test mode to avoid polluting isolated test databases.
        if not app.config.get("TESTING"):
            try:
                from juntos.seed import run as _seed_run

                _seed_run()
            except Exception:
                logger.warning(
                    "Failed to initialize Philadelphia Junto seed data on startup "
                    "(non-fatal). Run `flask seed` manually if seed commitments are "
                    "missing.",
                    exc_info=True,
                )

    return app
