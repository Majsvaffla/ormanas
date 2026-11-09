import asyncio
from machine import Pin, PWM

# Green and blue are crossed relative to the strip's silkscreen,
# because the pads were wired that way on both boards.
CHANNEL_PINS = {
    "red": 3,
    "green": 5,
    "blue": 4,
    "white": 2,
}
CHANNEL_NAMES = ("red", "green", "blue", "white")

GAMMA = 2.2
FADE_STEP_MILLISECONDS = 20

_outputs = {name: PWM(Pin(gpio), freq=1000) for name, gpio in CHANNEL_PINS.items()}
_levels = {name: 0 for name in CHANNEL_NAMES}


def current_levels():
    return dict(_levels)


def set_levels(levels):
    """Apply a partial mapping of channel name to level, 0-255."""
    for name, value in levels.items():
        if name not in _outputs:
            continue
        value = max(0, min(255, int(value)))
        _levels[name] = value
        _outputs[name].duty_u16(int((value / 255) ** GAMMA * 65535))


def all_off():
    set_levels({name: 0 for name in CHANNEL_NAMES})


async def fade_to(levels, duration_milliseconds):
    if duration_milliseconds <= 0:
        set_levels(levels)
        return

    start_levels = dict(_levels)
    target_levels = dict(_levels)
    for name, value in levels.items():
        if name in target_levels:
            target_levels[name] = max(0, min(255, int(value)))

    step_count = max(1, duration_milliseconds // FADE_STEP_MILLISECONDS)
    for step_index in range(1, step_count + 1):
        progress = step_index / step_count
        set_levels(
            {
                name: start_levels[name]
                + (target_levels[name] - start_levels[name]) * progress
                for name in CHANNEL_NAMES
            }
        )
        await asyncio.sleep_ms(FADE_STEP_MILLISECONDS)
