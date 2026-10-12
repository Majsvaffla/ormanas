from __future__ import annotations

from pathlib import Path
from typing import Final

from htpy import Element, body, button, div, h1, head, html, label, main, meta, script, style, title
from htpy import input as input_element
from markupsafe import Markup

CHANNEL_NAMES: Final = ("white", "red", "green", "blue")

STYLESHEET: Final = """
body { font-family: system-ui, sans-serif; max-width: 30em; margin: 2em auto; padding: 0 1em; }
label { display: block; margin: 1.5em 0; text-transform: capitalize; }
input[type=range] { width: 100%; }
button { padding: 0.6em 1.2em; font-size: 1em; }
"""

BROWSER_SCRIPT: Final = """
function setChannel(channel, value) {
  fetch('/set?' + channel + '=' + value);
}
function allOff() {
  fetch('/set?white=0&red=0&green=0&blue=0');
  document.querySelectorAll('input[type=range]').forEach(function (slider) {
    slider.value = 0;
  });
}
window.addEventListener('load', function () {
  fetch('/state').then(function (response) {
    return response.json();
  }).then(function (levels) {
    Object.keys(levels).forEach(function (channel) {
      var slider = document.querySelector('input[data-channel="' + channel + '"]');
      if (slider) { slider.value = levels[channel]; }
    });
  });
});
"""


def channel_slider(channel_name: str) -> Element:
    return label[
        channel_name,
        input_element(
            type="range",
            min="0",
            max="255",
            value="0",
            data_channel=channel_name,
            oninput="setChannel(this.dataset.channel, this.value)",
        ),
    ]


def build_document() -> Element:
    return html(lang="en")[
        head[
            meta(charset="utf-8"),
            meta(name="viewport", content="width=device-width,initial-scale=1"),
            title["Ormanäs"],
            style[Markup(STYLESHEET)],
        ],
        body[
            main[
                h1["Ormanäs"],
                div(id="channels")[[channel_slider(name) for name in CHANNEL_NAMES]],
                button(onclick="allOff()")["All off"],
            ],
            script[Markup(BROWSER_SCRIPT)],
        ],
    ]


def write_page(output_path: Path) -> None:
    output_path.write_text(str(build_document()), encoding="utf-8")


if __name__ == "__main__":
    write_page(Path(__file__).parent / "index.html")
