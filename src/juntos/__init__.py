import os

from flask import Flask

from juntos.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from juntos.models import db

    db.init_app(app)

    from juntos.routes import juntos, main, members

    app.register_blueprint(main.bp)
    app.register_blueprint(juntos.bp)
    app.register_blueprint(members.bp)

    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(uri[10:]), exist_ok=True)

    with app.app_context():
        db.create_all()

    return app
