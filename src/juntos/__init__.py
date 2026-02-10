from flask import Flask

from juntos.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from juntos.models import db

    db.init_app(app)

    from juntos.routes import main

    app.register_blueprint(main.bp)

    with app.app_context():
        db.create_all()

    return app
