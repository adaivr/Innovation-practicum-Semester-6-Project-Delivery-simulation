import unittest
from flask_testing import TestCase
from flask import Flask
from app.extensions import db


class TestExtensions(TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db.init_app(app)
        return app

    def setUp(self):
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_db_has_session(self):
        with self.app.app_context():
            self.assertTrue(hasattr(db, "session"))
            self.assertIsNotNone(db.session)


if __name__ == "__main__":
    unittest.main()
