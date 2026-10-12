serial_port="${SERIAL_PORT:-/dev/ttyACM0}"

if [[ -f wifi-credentials.env ]]; then
    # shellcheck disable=SC1091
    source wifi-credentials.env
fi

export WIFI_SSID WIFI_PASSWORD

echo "Building index.html"
python build.py

staging_directory="$(mktemp --directory)"
trap 'rm -rf "$staging_directory"' EXIT

echo "Rendering credentials"
python render_credentials.py "$staging_directory/wifi_credentials.py"

echo "Copying files to $serial_port"
mpremote connect "$serial_port" fs cp "$staging_directory/wifi_credentials.py" :wifi_credentials.py
mpremote connect "$serial_port" fs cp index.html :index.html
mpremote connect "$serial_port" fs cp pico.py :main.py

echo "Resetting"
mpremote connect "$serial_port" reset
