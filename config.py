import json
from paths import DATA_DIR

PATH = DATA_DIR / "config.json"
DEFAULTS = {
    "pet_name": "Dpet",
    "scale": 1.5,                     # size of the pet (1.25 tiny, 1.5 small, 2 medium, 3 large)
    "speed": 1.2,                     # walking speed (pixels per tick)
    "activity_gap_seconds": [40, 100],  # walking time between activities (eat / sit / nap)
    "jump_gap_seconds": [45, 120],      # time between jumps
    "wheel_on": True,                 # show the spinning wheel
    "bottle_on": True,                # show the water bottle
    "wheel_x": None,                  # saved positions (None = right corner)
    "bottle_x": None,
    "water_level": 1.0,
    "wheel_run_seconds": [12, 25],    # how long the hamster runs on the wheel
    "wheel_gap_minutes": [3, 6],      # it goes to run on the wheel every few minutes
    "drink_gap_minutes": [5, 9],      # and goes to drink every few minutes
    "water_minutes": 45,
    "study_minutes": 50,
    "sleep_time": "23:30",
    "reminders_enabled": True,
}


class Config(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        try:
            self.update(json.loads(PATH.read_text(encoding="utf-8")))
        except Exception:
            pass

    def save(self):
        try:
            PATH.write_text(json.dumps(dict(self), indent=2), encoding="utf-8")
        except Exception as e:
            print("Could not save config:", e)
