#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/.tmp/runtime_verification/${STAMP}"
COOKIE_JAR="${ARTIFACT_DIR}/cookies.txt"
ENV_FILE="${ROOT_DIR}/.env"

mkdir -p "${ARTIFACT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  bash "${ROOT_DIR}/deploy/bootstrap_env.sh"
fi

set -a
source "${ENV_FILE}"
set +a

if [[ -z "${APP_AES256_KEY_B64:-}" ]]; then
  echo "APP_AES256_KEY_B64 is not set. Export it before running this verifier." >&2
  exit 1
fi

echo "[1/8] Starting Docker stack"
docker compose -f "${ROOT_DIR}/docker-compose.yml" down -v > "${ARTIFACT_DIR}/docker_down.log" 2>&1 || true
docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --build | tee "${ARTIFACT_DIR}/docker_up.log"

echo "[2/8] Verifying health endpoint"
health_ok=0
for attempt in $(seq 1 30); do
  if curl -ksS "https://localhost:8443/api/health/" > "${ARTIFACT_DIR}/health.json"; then
    cat "${ARTIFACT_DIR}/health.json"
    health_ok=1
    break
  fi
  sleep 2
done
if [[ "${health_ok}" -ne 1 ]]; then
  echo "Health check failed after retries" >&2
  exit 1
fi

echo "[3/8] Verifying security config command"
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T backend \
  python manage.py check_security_config | tee "${ARTIFACT_DIR}/security_config_check.txt"

echo "[4/8] Fetching CSRF cookie"
curl -ksS -c "${COOKIE_JAR}" "https://localhost:8443/api/auth/csrf/" \
  | tee "${ARTIFACT_DIR}/csrf.json"

CSRF_TOKEN="$(awk '$6 == "csrftoken" {print $7}' "${COOKIE_JAR}" | tail -n 1)"

echo "[5/8] Logging in seeded org admin"
curl -ksS -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF_TOKEN}" \
  -d '{"username":"orgadmin","password":"SecurePass1234"}' \
  "https://localhost:8443/api/auth/login/" \
  | tee "${ARTIFACT_DIR}/login.json"

echo "[6/8] Verifying key authenticated API flows"
curl -ksS -b "${COOKIE_JAR}" "https://localhost:8443/api/access/me/roles/" \
  | tee "${ARTIFACT_DIR}/roles.json"
curl -ksS -b "${COOKIE_JAR}" "https://localhost:8443/api/trips/" \
  | tee "${ARTIFACT_DIR}/trips.json"
curl -ksS -b "${COOKIE_JAR}" "https://localhost:8443/api/jobs/" \
  | tee "${ARTIFACT_DIR}/jobs.json"

echo "[7/8] Verifying worker orchestration guarantees"
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T backend \
  python manage.py test tests.test_e2e_suite.EndToEndSuite.test_45_worker_runtime_path_enforces_per_org_concurrency_limit \
  tests.test_e2e_suite.EndToEndSuite.test_46_worker_runtime_path_blocks_dependencies_until_prereq_success -v 2 \
  | tee "${ARTIFACT_DIR}/worker_orchestration_tests.txt"

echo "[8/8] Runtime verification complete"
echo "Artifacts written to ${ARTIFACT_DIR}"
