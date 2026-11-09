import asyncio
import json
import network
import time
from machine import Pin

import device_config
import lights
import scheduler
import sequences

PAGE_PATH = "index.html"

status_led = Pin("LED", Pin.OUT)


def connect_to_wifi(timeout_seconds=20):
    wlan = network.WLAN(network.STA_IF)
    try:
        network.hostname(device_config.hostname)
    except Exception:
        pass
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(device_config.ssid, device_config.password)
        deadline = time.ticks_add(time.ticks_ms(), timeout_seconds * 1000)
        while not wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise RuntimeError("Wi-Fi connection timed out")
            time.sleep(0.2)
    return wlan.ifconfig()[0]


def synchronise_clock():
    try:
        import ntptime

        ntptime.settime()
        print("clock synchronised")
    except Exception as error:
        print("clock sync failed:", error)


def parse_query_string(path):
    if "?" not in path:
        return {}
    parameters = {}
    for pair in path.split("?", 1)[1].split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            parameters[key] = value
    return parameters


async def send_response(writer, body, content_type="application/json", status="200 OK"):
    writer.write(
        "HTTP/1.0 {}\r\nContent-Type: {}\r\nConnection: close\r\n\r\n".format(
            status, content_type
        ).encode()
    )
    if isinstance(body, str):
        body = body.encode()
    writer.write(body)
    await writer.drain()


async def send_page(writer):
    try:
        page_file = open(PAGE_PATH, "rb")
    except OSError:
        await send_response(
            writer, "index.html is missing", "text/plain", "404 Not Found"
        )
        return
    writer.write(
        b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
        b"Connection: close\r\n\r\n"
    )
    try:
        while True:
            chunk = page_file.read(512)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        page_file.close()


def status_document():
    now = scheduler.local_time()
    return {
        "hostname": device_config.hostname,
        "levels": lights.current_levels(),
        "sequence": sequences.running_name(),
        "clock_set": scheduler.clock_is_set(),
        "local_time": "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(
            now[0], now[1], now[2], now[3], now[4]
        ),
    }


async def route(method, path, body, writer):
    if path == "/" or path.startswith("/?"):
        await send_page(writer)

    elif path.startswith("/set"):
        sequences.stop()
        lights.set_levels(
            {
                name: int(value)
                for name, value in parse_query_string(path).items()
                if name in lights.CHANNEL_PINS and value.lstrip("-").isdigit()
            }
        )
        await send_response(writer, json.dumps(lights.current_levels()))

    elif path.startswith("/state"):
        await send_response(writer, json.dumps(lights.current_levels()))

    elif path.startswith("/status"):
        await send_response(writer, json.dumps(status_document()))

    elif path == "/stop":
        sequences.stop()
        await send_response(writer, json.dumps({"stopped": True}))

    elif path == "/sequences" and method == "GET":
        await send_response(writer, json.dumps(sequences.library))

    elif path == "/sequences" and method in ("PUT", "POST"):
        incoming = json.loads(body)
        if sequences.running_name() not in incoming:
            sequences.stop()
        sequences.library.clear()
        sequences.library.update(incoming)
        sequences.save()
        await send_response(writer, json.dumps(sequences.library))

    elif path.startswith("/sequences/") and path.endswith("/run"):
        name = path[len("/sequences/") : -len("/run")]
        try:
            sequences.start(name)
        except KeyError:
            await send_response(
                writer,
                json.dumps({"error": "no such sequence"}),
                status="404 Not Found",
            )
            return
        await send_response(writer, json.dumps({"running": name}))

    elif path == "/schedules" and method == "GET":
        await send_response(writer, json.dumps(scheduler.schedules))

    elif path == "/schedules" and method in ("PUT", "POST"):
        scheduler.schedules[:] = json.loads(body)
        scheduler.save()
        await send_response(writer, json.dumps(scheduler.schedules))

    else:
        await send_response(writer, "not found", "text/plain", "404 Not Found")


async def handle_client(reader, writer):
    try:
        request_line = await reader.readline()
        content_length = 0
        while True:
            header_line = await reader.readline()
            if not header_line or header_line == b"\r\n":
                break
            name, _, value = header_line.decode().partition(":")
            if name.strip().lower() == "content-length":
                content_length = int(value.strip())

        body = b""
        while len(body) < content_length:
            chunk = await reader.read(content_length - len(body))
            if not chunk:
                break
            body += chunk

        parts = request_line.decode().split(" ")
        if len(parts) < 2:
            await send_response(writer, "bad request", "text/plain", "400 Bad Request")
        else:
            await route(parts[0], parts[1], body.decode(), writer)
    except Exception as error:
        print("request failed:", error)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    address = connect_to_wifi()
    status_led.on()
    print("listening on http://{}/".format(address))

    synchronise_clock()
    await asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(scheduler.run_forever())

    while True:
        await asyncio.sleep(3600)
        synchronise_clock()


asyncio.run(main())
