#!/bin/sh
set -eu

DATA_DIR="${GEOHARVEST_DATA_DIR:-/app/data}"
DOWNLOADS_DIR="${GEOHARVEST_DOWNLOADS_DIR:-${DATA_DIR}/downloads}"
CATALOG_DIR="${GEOHARVEST_CATALOG_DIR:-${DATA_DIR}/catalog}"
AOIS_DIR="${GEOHARVEST_AOIS_DIR:-${DATA_DIR}/aois}"
PROCESSED_DIR="${GEOHARVEST_PROCESSED_DIR:-${DATA_DIR}/processed}"
CREDENTIALS_DIR="${GEOHARVEST_CREDENTIALS_DIR:-${DATA_DIR}/credentials}"
CUSTOM_DIR="${GEOHARVEST_CUSTOM_DIR:-${DATA_DIR}/custom}"

for dir in \
    "$DATA_DIR" \
    "$DOWNLOADS_DIR" \
    "$CATALOG_DIR" \
    "${CATALOG_DIR}/collections" \
    "${CATALOG_DIR}/toposheets" \
    "$AOIS_DIR" \
    "$PROCESSED_DIR" \
    "$CREDENTIALS_DIR" \
    "$CUSTOM_DIR"
do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
done

if [ "$#" -eq 0 ]; then
    exec python3 geoharvest.py \
        --host "${GEOHARVEST_HOST:-0.0.0.0}" \
        --port "${GEOHARVEST_PORT:-9009}" \
        --no-browser
fi

exec "$@"
