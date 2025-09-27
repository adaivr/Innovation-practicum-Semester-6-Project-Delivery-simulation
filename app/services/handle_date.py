import json
import os
from datetime import date, timedelta

DATE_FILE = "data/date.json"
SIMULATION_STEP = 1
SIMULATION_SPEED = 30
CURRENT_DATE = date.today()


def update_date(current_date=None, shift=SIMULATION_STEP):
    global CURRENT_DATE
    if current_date is None:
        current_date = CURRENT_DATE
    new_date = current_date + timedelta(days=shift)
    CURRENT_DATE = new_date
    data = {"date": new_date.isoformat()}
    with open(DATE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return new_date


def get_date():
    if not os.path.exists(DATE_FILE):
        os.makedirs(os.path.dirname(DATE_FILE), exist_ok=True)
        return update_date(shift=0)
    with open(DATE_FILE, "r") as f:
        data = json.load(f)
        return date.fromisoformat(data["date"])
