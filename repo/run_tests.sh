#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
HEALTH_URL="https://localhost:8443/api/health/"

cleanup_sensitive_artifacts() {
  bash "${ROOT_DIR}/deploy/scrub_sensitive_runtime.sh" >/dev/null 2>&1 || true
}

trap cleanup_sensitive_artifacts EXIT

echo "[0/8] Pre-cleaning sensitive runtime artifacts"
bash "${ROOT_DIR}/deploy/scrub_sensitive_runtime.sh"

echo "[1/8] Verifying no sensitive runtime artifacts"
bash "${ROOT_DIR}/deploy/check_no_sensitive_runtime_artifacts.sh"

echo "[2/8] Resetting Docker stack"
docker compose -f "${COMPOSE_FILE}" down -v --remove-orphans || true

echo "[3/8] Starting Docker services"
docker compose -f "${COMPOSE_FILE}" up -d --build

echo "[4/8] Waiting for HTTPS health endpoint"
health_ok=0
for attempt in $(seq 1 60); do
  if curl -fsSk "${HEALTH_URL}" > /dev/null; then
    health_ok=1
    break
  fi
  sleep 2
done

if [[ "${health_ok}" -ne 1 ]]; then
  echo "Health check failed after retries" >&2
  docker compose -f "${COMPOSE_FILE}" logs backend proxy
  exit 1
fi

echo "[5/8] Running backend test suite"
docker compose -f "${COMPOSE_FILE}" exec -T backend \
  env SESSION_REPLAY_REQUIRE_HEADERS=false python manage.py test tests -v 1

echo "[6/8] Running frontend test suite"
docker compose -f "${COMPOSE_FILE}" exec -T frontend npm run test:run

echo "[7/8] Running frontend production build"
docker compose -f "${COMPOSE_FILE}" exec -T frontend npm run build

echo "[8/8] Running real frontend-backend smoke"
bash "${ROOT_DIR}/deploy/smoke_frontend_backend.sh"

echo "Cleaning sensitive runtime artifacts created during tests"
bash "${ROOT_DIR}/deploy/scrub_sensitive_runtime.sh"
bash "${ROOT_DIR}/deploy/check_no_sensitive_runtime_artifacts.sh"

echo "All Docker tests passed"
