CHANNEL_NAMES = ("red", "green", "blue", "white")

# Longest suffix first, so "400ms" is not read as "400m" + "s".
DURATION_UNITS = (
    ("ms", 1),
    ("s", 1000),
    ("m", 60000),
    ("h", 3600000),
)

TIMING_KEYWORDS = ("fade", "hold")


class SequenceSyntaxError(Exception):
    def __init__(self, line_number, message):
        Exception.__init__(self, "line {}: {}".format(line_number, message))
        self.line_number = line_number


def parse_duration(text, line_number):
    for suffix, multiplier in DURATION_UNITS:
        if text.endswith(suffix):
            digits = text[: -len(suffix)]
            if digits.isdigit():
                return int(digits) * multiplier
            break
    raise SequenceSyntaxError(
        line_number, "bad duration {!r}, expected e.g. 400ms, 3s, 2m".format(text)
    )


def parse_level(text, line_number):
    if not text.isdigit():
        raise SequenceSyntaxError(
            line_number, "bad level {!r}, expected a number 0-255".format(text)
        )
    value = int(text)
    if value > 255:
        raise SequenceSyntaxError(line_number, "level {} is above 255".format(value))
    return value


def parse_levels(tokens, line_number):
    if not tokens:
        raise SequenceSyntaxError(line_number, "step has no levels")

    if "=" in tokens[0]:
        levels = {}
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
    levels = {}
    for index, name in enumerate(CHANNEL_NAMES):
        levels[name] = parse_level(tokens[index], line_number)
    return levels


def split_step_tokens(tokens):
    for index, token in enumerate(tokens):
        if token in TIMING_KEYWORDS:
            return tokens[:index], tokens[index:]
    return tokens, []


def parse_timings(tokens, line_number):
    timings = {}
    remaining = list(tokens)
    while remaining:
        keyword = remaining.pop(0)
        if not remaining:
            raise SequenceSyntaxError(line_number, "{} needs a duration".format(keyword))
        timings["{}_milliseconds".format(keyword)] = parse_duration(
            remaining.pop(0), line_number
        )
    return timings


def parse_step(tokens, line_number):
    level_tokens, timing_tokens = split_step_tokens(tokens)
    step = {"levels": parse_levels(level_tokens, line_number)}
    step.update(parse_timings(timing_tokens, line_number))
    return step


def parse_sequences(source):
    library = {}
    current_steps = None

    for line_number, raw_line in enumerate(source.splitlines()):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = line.split()
        if tokens[0] == "sequence":
            if len(tokens) < 2:
                raise SequenceSyntaxError(line_number + 1, "sequence needs a name")
            current_steps = []
            library[tokens[1]] = {
                "repeat": "repeat" in tokens[2:],
                "steps": current_steps,
            }
        else:
            if current_steps is None:
                raise SequenceSyntaxError(line_number + 1, "step outside any sequence")
            current_steps.append(parse_step(tokens, line_number + 1))

    return library