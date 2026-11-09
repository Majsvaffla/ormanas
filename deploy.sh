usage() {
    echo "usage: deploy <hostname>" >&2
    exit 64
}

device_hostname="${1:-}"

if [[ -z "$device_hostname" ]]; then
    usage
fi

serial_port="${SERIAL_PORT:-/dev/ttyACM0}"

if [[ -f wifi-credentials.env ]]; then
    # shellcheck disable=SC1091
    source wifi-credentials.env
fi

export WIFI_SSID WIFI_PASSWORD

staging_directory="$(mktemp --directory)"
trap 'rm -rf "$staging_directory"' EXIT

echo "Building index.html"
python build_markup.py > "$staging_directory/index.html"

echo "Rendering device config for $device_hostname"
python render_device_config.py "$device_hostname" > "$staging_directory/device_config.py"

echo "Copying files to $serial_port"
mpremote connect "$serial_port" fs cp "$staging_directory/device_config.py" :device_config.py
mpremote connect "$serial_port" fs cp "$staging_directory/index.html" :index.html
mpremote connect "$serial_port" fs cp pico.py :main.py

echo "Resetting"
mpremote connect "$serial_port" reset
