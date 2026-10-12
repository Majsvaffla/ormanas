import json
import network
import socket
import time
from machine import Pin, PWM

import wifi_credentials

CHANNEL_PINS = {
    "red": 3,
    "green": 4,
    "blue": 5,
    "white": 2,
}

GAMMA = 2.2
PAGE_PATH = "index.html"

pwm_outputs = {name: PWM(Pin(gpio), freq=1000) for name, gpio in CHANNEL_PINS.items()}
levels = {name: 0 for name in CHANNEL_PINS}


def set_channel(channel_name: str, value: int) -> None:
    """Set one channel, 0-255, gamma corrected so dimming looks linear."""
    value = max(0, min(255, int(value)))
    levels[channel_name] = value
    pwm_outputs[channel_name].duty_u16(int((value / 255) ** GAMMA * 65535))


def connect_to_wifi(timeout_seconds: int = 20) -> str:
    wlan = network.WLAN(network.STA_IF)
    try:
        network.hostname("ormanas")
    except Exception:
        pass
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(wifi_credentials.ssid, wifi_credentials.password)
        deadline = time.ticks_add(time.ticks_ms(), timeout_seconds * 1000)
        while not wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise RuntimeError("Wi-Fi connection timed out")
            time.sleep(0.2)
    status_led = Pin("LED", Pin.OUT)
    status_led.on()
    return wlan.ifconfig()[0]


def parse_query_string(path: str) -> dict:
    if "?" not in path:
        return {}
    parameters = {}
    for pair in path.split("?", 1)[1].split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            parameters[key] = value
    return parameters


def apply_parameters(parameters: dict) -> None:
    for channel_name, raw_value in parameters.items():
        if channel_name in pwm_outputs:
            try:
                set_channel(channel_name, int(raw_value))
            except ValueError:
                pass


def send_header(connection, content_type: str, status: str = "200 OK") -> None:
    connection.send(
        "HTTP/1.0 {}\r\nContent-Type: {}\r\nConnection: close\r\n\r\n".format(
            status, content_type
        )
    )


def send_page(connection) -> None:
    try:
        page_file = open(PAGE_PATH, "rb")
    except OSError:
        send_header(connection, "text/plain", "404 Not Found")
        connection.send("index.html is missing from the board")
        return
    send_header(connection, "text/html; charset=utf-8")
    try:
        while True:
            chunk = page_file.read(512)
            if not chunk:
                break
            connection.send(chunk)
    finally:
        page_file.close()


def handle_connection(connection) -> None:
    request_line = connection.readline() or b""
    while True:
        header_line = connection.readline()
        if not header_line or header_line == b"\r\n":
            break

    try:
        path = request_line.decode().split(" ")[1]
    except IndexError:
        send_header(connection, "text/plain", "400 Bad Request")
        return

    if path.startswith("/set"):
        apply_parameters(parse_query_string(path))
        send_header(connection, "application/json")
        connection.send(json.dumps(levels))
    elif path.startswith("/state"):
        send_header(connection, "application/json")
        connection.send(json.dumps(levels))
    elif path == "/" or path.startswith("/?"):
        send_page(connection)
    else:
        send_header(connection, "text/plain", "404 Not Found")
        connection.send("not found")


def serve_forever(port: int = 80) -> None:
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", port))
    listener.listen(2)
    while True:
        connection = None
        try:
            connection, _ = listener.accept()
            handle_connection(connection)
        except Exception as error:
            print("request failed:", error)
        finally:
            if connection is not None:
                connection.close()


address = connect_to_wifi()
print("listening on http://{}/".format(address))
serve_forever()
