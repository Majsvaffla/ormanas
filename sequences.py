import asyncio

import lights
import storage

SEQUENCES_PATH = "sequences.json"

library = storage.load_json(SEQUENCES_PATH, {})

_running_task = None
_running_name = None
_generation = 0


def save():
    storage.save_json(SEQUENCES_PATH, library)


def running_name():
    return _running_name


async def _play(name, generation):
    global _running_name
    try:
        sequence = library[name]
        steps = sequence.get("steps", [])
        repeat = bool(sequence.get("repeat", False))
        while True:
            for step in steps:
                await lights.fade_to(
                    step.get("levels", {}), int(step.get("fade_milliseconds", 0))
                )
                hold_milliseconds = int(step.get("hold_milliseconds", 0))
                if hold_milliseconds:
                    await asyncio.sleep_ms(hold_milliseconds)
            if not repeat:
                break
    finally:
        # Only clear the name if a newer run has not already replaced us.
        if generation == _generation:
            _running_name = None


def stop():
    global _running_task, _running_name, _generation
    _generation += 1
    if _running_task is not None:
        _running_task.cancel()
        _running_task = None
    _running_name = None


def start(name):
    global _running_task, _running_name
    if name not in library:
        raise KeyError(name)
    stop()
    _running_name = name
    _running_task = asyncio.create_task(_play(name, _generation))
