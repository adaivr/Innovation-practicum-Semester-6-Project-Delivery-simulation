from flask import Flask
from app.extensions import db
from app.models import *
from app.routes import bp


def create_app(test=False):
    app = Flask(__name__)
    if test:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
    else:
        app.config.from_pyfile("config.py")

    db.init_app(app)

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        set_map()
        update_routes_status()

    return app
