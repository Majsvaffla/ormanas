from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Final

CHANNEL_NAMES: Final[tuple[str, ...]] = ("red", "green", "blue", "white")

DURATION_UNITS: Final[dict[str, int]] = {
    "ms": 1,
    "s": 1000,
    "m": 60_000,
    "h": 3_600_000,
}

DURATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(\d+)(ms|s|m|h)$")

TIMING_KEYWORDS: Final[tuple[str, ...]] = ("fade", "hold")


class SequenceSyntaxError(SystemExit):
    def __init__(self, line_number: int, message: str) -> None:
        super().__init__("line {}: {}".format(line_number, message))


def parse_duration(text: str, line_number: int) -> int:
    match = DURATION_PATTERN.match(text)
    if match is None:
        raise SequenceSyntaxError(
            line_number, "bad duration {!r}, expected e.g. 400ms, 3s, 2m".format(text)
        )
    return int(match.group(1)) * DURATION_UNITS[match.group(2)]


def parse_level(text: str, line_number: int) -> int:
    try:
        value = int(text)
    except ValueError:
        raise SequenceSyntaxError(
            line_number, "bad level {!r}, expected a number 0-255".format(text)
        )
    if not 0 <= value <= 255:
        raise SequenceSyntaxError(line_number, "level {} is outside 0-255".format(value))
    return value


def parse_levels(tokens: list[str], line_number: int) -> dict[str, int]:
    if not tokens:
        raise SequenceSyntaxError(line_number, "step has no levels")

    if "=" in tokens[0]:
        levels: dict[str, int] = {}
        for token in tokens:
            name, _, raw_value = token.partition("=")
            if name not in CHANNEL_NAMES:
                raise SequenceSyntaxError(
                    line_number,
                    "unknown channel {!r}, expected one of {}".format(
                        name, ", ".join(CHANNEL_NAMES)
                    ),
                )
            levels[name] = parse_level(raw_value, line_number)
        return levels

    if len(tokens) != len(CHANNEL_NAMES):
        raise SequenceSyntaxError(
            line_number,
            "expected {} levels in {} order, got {}".format(
                len(CHANNEL_NAMES), "/".join(CHANNEL_NAMES), len(tokens)
            ),
        )
    return {
        name: parse_level(token, line_number)
        for name, token in zip(CHANNEL_NAMES, tokens)
    }


def split_step_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    for index, token in enumerate(tokens):
        if token in TIMING_KEYWORDS:
            return tokens[:index], tokens[index:]
    return tokens, []


def parse_timings(tokens: list[str], line_number: int) -> dict[str, int]:
    timings: dict[str, int] = {}
    remaining = list(tokens)
    while remaining:
        keyword = remaining.pop(0)
        if not remaining:
            raise SequenceSyntaxError(line_number, "{} needs a duration".format(keyword))
        timings["{}_milliseconds".format(keyword)] = parse_duration(
            remaining.pop(0), line_number
        )
    return timings


def parse_step(tokens: list[str], line_number: int) -> dict[str, object]:
    level_tokens, timing_tokens = split_step_tokens(tokens)
    step: dict[str, object] = {"levels": parse_levels(level_tokens, line_number)}
    step.update(parse_timings(timing_tokens, line_number))
    return step


def parse_sequences(source: str) -> dict[str, object]:
    library: dict[str, object] = {}
    current_steps: list[dict[str, object]] | None = None

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = line.split()
        if tokens[0] == "sequence":
            if len(tokens) < 2:
                raise SequenceSyntaxError(line_number, "sequence needs a name")
            current_steps = []
            library[tokens[1]] = {
                "repeat": "repeat" in tokens[2:],
                "steps": current_steps,
            }
        else:
            if current_steps is None:
                raise SequenceSyntaxError(line_number, "step outside any sequence")
            current_steps.append(parse_step(tokens, line_number))

    return library


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile sequences.txt to JSON.")
    parser.add_argument("source_path", type=Path)
    parser.add_argument("output_path", type=Path)
    arguments = parser.parse_args()

    library = parse_sequences(arguments.source_path.read_text(encoding="utf-8"))
    arguments.output_path.write_text(json.dumps(library), encoding="utf-8")
    print("compiled {} sequences".format(len(library)))


if __name__ == "__main__":
    main()