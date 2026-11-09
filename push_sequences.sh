usage() {
    echo "usage: push [host ...]" >&2
    echo "       with no arguments, pushes to PICO_HOSTS from devices.env" >&2
    exit 64
}

if [[ -f devices.env ]]; then
    # shellcheck disable=SC1091
    source devices.env
fi

if [[ $# -gt 0 ]]; then
    target_hosts=("$@")
elif [[ -n "${PICO_HOSTS:-}" ]]; then
    read -r -a target_hosts <<< "$PICO_HOSTS"
else
    usage
fi

staging_directory="$(mktemp --directory)"
trap 'rm -rf "$staging_directory"' EXIT

echo "Compiling sequences"
python parse_sequences.py sequences.txt "$staging_directory/sequences.json"

for host in "${target_hosts[@]}"; do
    url="http://$host.local"
    echo "Pushing sequences to $host"
    curl --fail --silent --show-error --max-time 10 \
        -X PUT "$url/sequences" \
        -H 'Content-Type: application/json' \
        --data-binary "@$staging_directory/sequences.json" \
        --output /dev/null

    if [[ -f schedules.json ]]; then
        echo "Pushing schedules to $host"
        curl --fail --silent --show-error --max-time 10 \
            -X PUT "$url/schedules" \
            -H 'Content-Type: application/json' \
            --data-binary @schedules.json \
            --output /dev/null
    fi

    echo "Done with $host"
done
