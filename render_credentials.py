from __future__ import annotations

import argparse
import os
from pathlib import Path


def render_credentials_module(ssid: str, password: str) -> str:
    """Render a MicroPython module defining the Wi-Fi credentials.

    Values go through repr() so quotes, backslashes and non-ASCII
    characters survive intact.
    """
    return "ssid = {!r}\npassword = {!r}\n".format(ssid, password)


def read_environment_variable(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            "{} is not set — put it in wifi-credentials.env or export it".format(name)
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write wifi_credentials.py from the environment."
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="where to write the generated module",
    )
    arguments = parser.parse_args()

    module_source = render_credentials_module(
        ssid=read_environment_variable("WIFI_SSID"),
        password=read_environment_variable("WIFI_PASSWORD"),
    )
    arguments.output_path.write_text(module_source, encoding="utf-8")


if __name__ == "__main__":
    main()
