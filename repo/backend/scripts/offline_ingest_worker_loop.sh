#!/usr/bin/env sh
set -eu

echo "Starting offline ingest worker (scheduled folder scans enabled)"
python manage.py run_offline_ingest_worker --schedule --interval-seconds "${OFFLINE_INGEST_INTERVAL_SECONDS:-30}"
