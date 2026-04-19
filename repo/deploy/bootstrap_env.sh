#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE_FILE="${ROOT_DIR}/.env.example"

if [[ ! -f "${ENV_EXAMPLE_FILE}" ]]; then
  echo "Missing ${ENV_EXAMPLE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_EXAMPLE_FILE}" "${ENV_FILE}"
  echo "Created .env from .env.example"
fi

python3 - "${ENV_FILE}" <<'PY'
import base64
import os
import secrets
import sys
from pathlib import Path


env_path = Path(sys.argv[1])
raw = env_path.read_text(encoding="utf-8")
lines = raw.splitlines()

placeholders = {
    "",
    "change-me",
    "change-me-in-production",
    "replace-me",
    "changeme",
    "default",
    "replace-with-strong-db-password",
    "replace-with-strong-root-password",
    "replace-with-strong-django-secret",
    "replace-with-strong-passphrase",
    "replace-with-generated-key",
    "replace-with-unique-key",
    "harborops_dev_db_password_local_only",
    "harborops_dev_root_password_local_only",
    "django-insecure-harborops-local-dev-secret-key-2026",
    "harborops-local-backup-passphrase-2026",
}


def parse_env(content_lines):
    key_to_index = {}
    key_to_value = {}
    for index, line in enumerate(content_lines):
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        key_to_index[key] = index
        key_to_value[key] = value.strip()
    return key_to_index, key_to_value


def is_placeholder(value):
    candidate = (value or "").strip().strip('"').strip("'")
    lowered = candidate.lower()
    return lowered in placeholders or lowered.startswith("replace-with-")


def invalid_aes_key(value):
    candidate = (value or "").strip().strip('"').strip("'")
    if is_placeholder(candidate):
        return True
    try:
        decoded = base64.b64decode(candidate, validate=True)
    except Exception:
        return True
    return len(decoded) != 32


key_to_index, key_to_value = parse_env(lines)
generated = {}


def upsert(key, value):
    entry = f"{key}={value}"
    if key in key_to_index:
        lines[key_to_index[key]] = entry
    else:
        lines.append(entry)
        key_to_index[key] = len(lines) - 1
    key_to_value[key] = value


if invalid_aes_key(key_to_value.get("APP_AES256_KEY_B64", "")):
    upsert("APP_AES256_KEY_B64", base64.b64encode(os.urandom(32)).decode("ascii"))
    generated["APP_AES256_KEY_B64"] = "generated"

if is_placeholder(key_to_value.get("DJANGO_SECRET_KEY", "")):
    upsert("DJANGO_SECRET_KEY", secrets.token_urlsafe(64))
    generated["DJANGO_SECRET_KEY"] = "generated"

if is_placeholder(key_to_value.get("MYSQL_PASSWORD", "")):
    upsert("MYSQL_PASSWORD", secrets.token_urlsafe(32))
    generated["MYSQL_PASSWORD"] = "generated"

root_password = key_to_value.get("MYSQL_ROOT_PASSWORD", "")
if is_placeholder(root_password):
    root_password = secrets.token_urlsafe(32)
    upsert("MYSQL_ROOT_PASSWORD", root_password)
    generated["MYSQL_ROOT_PASSWORD"] = "generated"

admin_password = key_to_value.get("DB_ADMIN_PASSWORD", "")
if is_placeholder(admin_password) or admin_password != root_password:
    upsert("DB_ADMIN_PASSWORD", root_password)
    generated["DB_ADMIN_PASSWORD"] = "synchronized"

if is_placeholder(key_to_value.get("BACKUP_PASSPHRASE", "")):
    upsert("BACKUP_PASSPHRASE", secrets.token_urlsafe(36))
    generated["BACKUP_PASSPHRASE"] = "generated"

env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

if generated:
    print("Updated .env secrets:")
    for key in sorted(generated):
        print(f"- {key}: {generated[key]}")
else:
    print(".env secrets already valid; no changes made")
PY

echo "Run: docker compose run --rm backend python manage.py check_security_config"
