import json


def load_json(path, default):
    try:
        with open(path) as stored_file:
            return json.load(stored_file)
    except (OSError, ValueError):
        return default


def save_json(path, value):
    with open(path, "w") as stored_file:
        json.dump(value, stored_file)
