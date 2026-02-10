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

    app.instance_path and os.makedirs(app.instance_path, exist_ok=True)

    with app.app_context():
        db.create_all()

    return app
