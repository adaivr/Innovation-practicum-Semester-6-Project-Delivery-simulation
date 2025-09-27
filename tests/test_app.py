import unittest
from flask_testing import TestCase
from app import create_app


class TestApp(TestCase):
    def create_app(self):
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    def test_app_creation(self):
        self.assertIsNotNone(self.app)
        self.assertIn("main", self.app.blueprints)


if __name__ == "__main__":
    unittest.main()
