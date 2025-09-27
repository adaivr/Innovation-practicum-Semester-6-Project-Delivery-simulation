import unittest
from flask_testing import TestCase
from app import create_app
from app.extensions import db
from app.models import City
from flask import Flask


class TestRoutes(TestCase):
    def create_app(self):
        app = create_app(True)
        return app

    def setUp(self):
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_index(self):
        with self.app.app_context():
            resp = self.client.get("/")
            self.assertEqual(resp.status_code, 200)

    def test_cities_and_map(self):
        with self.app.app_context():
            city_A = City(city_name="A", city_lat=10, city_lon=20)
            city_B = City(city_name="B", city_lat=20, city_lon=20)
            db.session.add_all([city_A, city_B])
            db.session.commit()

            resp = self.client.get("/cities")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("cityName", resp.json[0])

            resp = self.client.get("/map")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("cities", resp.json)

    def test_date_and_delete(self):
        with self.app.app_context():
            resp = self.client.post("/date", json={"value": 1})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("date", resp.json)

            resp = self.client.post("/delete")
            self.assertEqual(resp.json["status"], "ok")

    def test_orders_and_send(self):
        with self.app.app_context():
            resp = self.client.get("/orders")
            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(resp.json, list)

            resp = self.client.post("/send", json=[])
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json["status"], "ok")


if __name__ == "__main__":
    unittest.main()
    