from __future__ import annotations

import argparse
import os
from pathlib import Path


def render_device_config_module(ssid: str, password: str, hostname: str) -> str:
    """Render a MicroPython module holding this board's configuration.

    Values go through repr() so quotes, backslashes and non-ASCII
    characters survive intact.
    """
    return "ssid = {!r}\npassword = {!r}\nhostname = {!r}\n".format(
        ssid, password, hostname
    )


def read_environment_variable(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            "{} is not set — put it in wifi-credentials.env or export it".format(name)
        )
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write device_config.py for one Pico."
    )
    parser.add_argument("--hostname", required=True, help="hostname for this board")
    parser.add_argument(
        "output_path",
        type=Path,
        help="where to write the generated module",
    )
    arguments = parser.parse_args()

    module_source = render_device_config_module(
        ssid=read_environment_variable("WIFI_SSID"),
        password=read_environment_variable("WIFI_PASSWORD"),
        hostname=arguments.hostname,
    )
    arguments.output_path.write_text(module_source, encoding="utf-8")

if __name__ == "__main__":
    main()
