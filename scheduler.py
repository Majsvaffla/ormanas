import asyncio
import time

import lights
import sequences
import storage

SCHEDULES_PATH = "schedules.json"
CHECK_INTERVAL_SECONDS = 20

schedules = storage.load_json(SCHEDULES_PATH, [])


def save():
    storage.save_json(SCHEDULES_PATH, schedules)


def _last_sunday(year, month):
    for day in range(31, 24, -1):
        timestamp = time.mktime((year, month, day, 12, 0, 0, 0, 0))
        if time.gmtime(timestamp)[6] == 6:
            return day
    return 31


def _is_summer_time(utc):
    """EU rule: last Sunday in March 01:00 UTC to last Sunday in October 01:00 UTC."""
    year, month, day, hour = utc[0], utc[1], utc[2], utc[3]
    if month < 3 or month > 10:
        return False
    if 3 < month < 10:
        return True
    changeover_day = _last_sunday(year, month)
    if month == 3:
        return (day, hour) >= (changeover_day, 1)
    return (day, hour) < (changeover_day, 1)


def local_time():
    utc = time.gmtime()
    offset_seconds = (2 if _is_summer_time(utc) else 1) * 3600
    return time.gmtime(time.mktime(utc) + offset_seconds)


def clock_is_set():
    return time.gmtime()[0] >= 2024


def apply_action(action):
    action_type = action.get("type")
    if action_type == "sequence":
        sequences.start(action["name"])
    elif action_type == "levels":
        sequences.stop()
        lights.set_levels(action.get("levels", {}))
    elif action_type == "off":
        sequences.stop()
        lights.all_off()


async def run_forever():
    already_fired = {}
    while True:
        if clock_is_set():
            now = local_time()
            minute_stamp = (now[0], now[1], now[2], now[3], now[4])
            # MicroPython counts Monday as 0; schedules use ISO numbering.
            weekday = now[6] + 1
            for entry in schedules:
                if not entry.get("enabled", True):
                    continue
                try:
                    hour, minute = [int(part) for part in entry["time"].split(":")]
                except (KeyError, ValueError):
                    continue
                if (now[3], now[4]) != (hour, minute):
                    continue
                # days are ISO: 1 = Monday ... 7 = Sunday
                days = entry.get("days")
                if days and weekday not in days:
                    continue
                if already_fired.get(entry.get("id")) == minute_stamp:
                    continue
                already_fired[entry.get("id")] = minute_stamp
                try:
                    apply_action(entry.get("action", {}))
                except Exception as error:
                    print("schedule failed:", error)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
