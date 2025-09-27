import os
import json
import tempfile
import unittest
from datetime import date, timedelta

from flask_testing import TestCase
from flask import Flask

import app.services.handle_date as handle_date


class TestHandleDate(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        handle_date.DATE_FILE = os.path.join(self.tmpdir.name, "date.json")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_update_date_creates_file(self):
        new_date = handle_date.update_date(current_date=date(2025, 9, 19), shift=1)
        self.assertEqual(new_date, date(2025, 9, 20))

        with open(handle_date.DATE_FILE) as f:
            data = json.load(f)
        self.assertEqual(data["date"], "2025-09-20")

    def test_update_date_changes_global_current_date(self):
        old_date = handle_date.CURRENT_DATE
        new_date = handle_date.update_date(current_date=old_date, shift=3)
        self.assertEqual(new_date, old_date + timedelta(days=3))
        self.assertEqual(handle_date.CURRENT_DATE, new_date)

    def test_get_date_creates_file_if_missing(self):
        if os.path.exists(handle_date.DATE_FILE):
            os.remove(handle_date.DATE_FILE)
        result = handle_date.get_date()
        self.assertIsInstance(result, date)
        self.assertTrue(os.path.exists(handle_date.DATE_FILE))

    def test_get_date_reads_existing_file(self):
        current_date = date(2025, 9, 19)
        with open(handle_date.DATE_FILE, "w") as f:
            json.dump({"date": current_date.isoformat()}, f)

        result = handle_date.get_date()
        self.assertEqual(result, current_date)


if __name__ == "__main__":
    unittest.main()
