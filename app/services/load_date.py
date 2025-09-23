import json
from datetime import datetime

DATE_FILE = "data/date.json"

def load_date():
    with open(DATE_FILE, "r") as f:
        data = json.load(f)
        return datetime.fromisoformat(data["date"])


def save_date(date):
    data = {"date": date.isoformat()}
    with open(DATE_FILE, "w") as f:
        json.dump(data, f, indent=4)
