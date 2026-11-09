from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from markupsafe import Markup

from htpy import (
    Element,
    body,
    button,
    div,
    h1,
    h2,
    head,
    html,
    label,
    main,
    meta,
    p,
    script,
    style,
    title,
)
from htpy import input as input_element

CHANNEL_NAMES: Final[tuple[str, ...]] = ("red", "green", "blue", "white")

SEND_INTERVAL_MILLISECONDS: Final[int] = 120

STYLESHEET: Final[str] = """
body { font-family: system-ui, sans-serif; max-width: 32em; margin: 2em auto; padding: 0 1em; }
label { display: block; margin: 1.5em 0; text-transform: capitalize; }
input[type=range] { width: 100%; }
h2 { font-size: 1em; text-transform: uppercase; letter-spacing: 0.08em;
     opacity: 0.6; margin-top: 2em; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(8em, 1fr)); gap: 0.6em; }
button { padding: 0.8em 1.4em; font-size: 1em; border: 1px solid #8884;
         border-radius: 0.5em; background: #8881; cursor: pointer; }
button:active { background: #8884; }
#status { margin-top: 2em; font-size: 0.85em; opacity: 0.6; }
"""

BROWSER_SCRIPT: Final[str] = """
var SEND_INTERVAL = %d;

var pendingLevels = {};
var requestInFlight = false;
var lastSentAt = 0;
var flushTimer = null;

function flush() {
  flushTimer = null;
  if (requestInFlight) { return; }
  var channels = Object.keys(pendingLevels);
  if (channels.length === 0) { return; }

  var query = channels.map(function (channel) {
    return channel + '=' + pendingLevels[channel];
  }).join('&');
  pendingLevels = {};

  requestInFlight = true;
  lastSentAt = Date.now();
  fetch('/set?' + query).then(function (response) {
    return response.json();
  }).catch(function () {
    return null;
  }).then(function () {
    requestInFlight = false;
    if (Object.keys(pendingLevels).length > 0) { scheduleFlush(); }
  });
}

function scheduleFlush() {
  if (flushTimer !== null) { return; }
  var waitFor = Math.max(0, SEND_INTERVAL - (Date.now() - lastSentAt));
  flushTimer = setTimeout(flush, waitFor);
}

function setChannel(channel, value) {
  pendingLevels[channel] = value;
  scheduleFlush();
}

function allOff() {
  CHANNELS.forEach(function (channel) {
    pendingLevels[channel] = 0;
    var slider = document.getElementById('slider-' + channel);
    if (slider) { slider.value = 0; }
  });
  scheduleFlush();
}

function runSequence(name) {
  fetch('/sequences/' + name + '/run').then(refreshStatus);
}

function stopSequence() {
  fetch('/stop').then(refreshStatus);
}

function loadSequences() {
  fetch('/sequences').then(function (response) {
    return response.json();
  }).then(function (library) {
    var container = document.getElementById('sequences');
    container.textContent = '';
    Object.keys(library).forEach(function (name) {
      var element = document.createElement('button');
      element.textContent = name;
      element.onclick = function () { runSequence(name); };
      container.appendChild(element);
    });
  });
}

function refreshStatus() {
  fetch('/status').then(function (response) {
    return response.json();
  }).then(function (status) {
    var running = status.sequence ? 'running ' + status.sequence : 'no sequence';
    document.getElementById('status').textContent =
      status.hostname + ' - ' + running + ' - ' + status.local_time;
  });
}

window.addEventListener('load', function () {
  fetch('/state').then(function (response) {
    return response.json();
  }).then(function (levels) {
    Object.keys(levels).forEach(function (channel) {
      var slider = document.getElementById('slider-' + channel);
      if (slider) { slider.value = levels[channel]; }
    });
  });
  loadSequences();
  refreshStatus();
});
""" % SEND_INTERVAL_MILLISECONDS


def channel_declaration() -> str:
    names = ", ".join("'{}'".format(name) for name in CHANNEL_NAMES)
    return "var CHANNELS = [{}];\n".format(names)


def channel_slider(channel_name: str) -> Element:
    return label[
        channel_name,
        input_element(
            type="range",
            min="0",
            max="255",
            value="0",
            id="slider-{}".format(channel_name),
            oninput="setChannel('{}', this.value)".format(channel_name),
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
                div(id="channels")[
                    [channel_slider(name) for name in CHANNEL_NAMES]
                ],
                p[button(onclick="allOff()")["All off"]],
                h2["Sequences"],
                div(id="sequences", class_="grid"),
                p[button(onclick="stopSequence()")["Stop sequence"]],
                p(id="status"),
            ],
            script[Markup(channel_declaration() + BROWSER_SCRIPT)],
        ],
    ]


if __name__ == "__main__":
    sys.stdout.write(str(build_document()))
