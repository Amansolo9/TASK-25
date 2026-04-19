#!/bin/sh
set -e

echo "Waiting for MySQL at ${DB_HOST}:${DB_PORT}..."
python - <<'PY'
import os
import time

import pymysql

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "harborops")
password = os.environ.get("DB_PASSWORD", "harborops_dev_password")
name = os.environ.get("DB_NAME", "harborops")

for attempt in range(120):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=name,
            connect_timeout=2,
            ssl_disabled=True,
        )
        conn.close()
        print("MySQL is ready.")
        break
    except Exception as exc:
        if attempt == 119:
            raise
        print(f"Waiting for MySQL ({attempt + 1}/120): {exc}")
        time.sleep(1)
PY

echo "Validating security configuration..."
python manage.py check_security_config

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Bootstrapping organization and permissions..."
python manage.py bootstrap_organization
python manage.py bootstrap_access
python manage.py bootstrap_demo_users

echo "Starting HarborOps backend..."
exec gunicorn harborops_backend.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
