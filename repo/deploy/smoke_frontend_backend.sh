#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://localhost:8443}"
USERNAME="${SMOKE_USERNAME:-orgadmin}"
PASSWORD="${SMOKE_PASSWORD:-SecurePass1234}"

COOKIE_JAR="$(mktemp)"
trap 'rm -f "${COOKIE_JAR}"' EXIT

extract_csrf() {
  # Parses {"csrfToken": "..."} without needing host python/jq.
  local raw="$1"
  raw="${raw#*\"csrfToken\"*:}"
  raw="${raw#*\"}"
  printf '%s' "${raw%%\"*}"
}

hmac_sha256_hex() {
  # Args: secret payload  -> hex digest (uses openssl, universally available).
  local secret="$1" payload="$2"
  printf '%s' "${payload}" | openssl dgst -sha256 -hmac "${secret}" -hex \
    | awk '{print $NF}'
}

generate_nonce() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
  else
    od -An -N16 -tx1 /dev/urandom | tr -d ' \n' \
      | sed 's/\(........\)\(....\)\(....\)\(....\)\(............\)/\1-\2-\3-\4-\5/'
  fi
}

echo "Checking frontend shell"
front_code="$(curl -sk -o /tmp/harborops_frontend_smoke.html -w "%{http_code}" "${BASE_URL}/")"
if [[ "${front_code}" != "200" ]]; then
  echo "Frontend shell check failed with status ${front_code}" >&2
  exit 1
fi

echo "Fetching CSRF token"
csrf_json="$(curl -sk -c "${COOKIE_JAR}" "${BASE_URL}/api/auth/csrf/")"
csrf_token="$(extract_csrf "${csrf_json}")"

echo "Logging in via real backend"
login_payload="{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
login_code="$(curl -sk -o /tmp/harborops_login_smoke.json -w "%{http_code}" -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" -H "Content-Type: application/json" -H "X-CSRFToken: ${csrf_token}" -H "Referer: ${BASE_URL}/" -X POST "${BASE_URL}/api/auth/login/" --data "${login_payload}")"
if [[ "${login_code}" != "200" ]]; then
  echo "Login smoke failed with status ${login_code}" >&2
  exit 1
fi

csrf_json="$(curl -sk -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" "${BASE_URL}/api/auth/csrf/")"
csrf_token="$(extract_csrf "${csrf_json}")"

echo "Checking role-gated backend context"
roles_code="$(curl -sk -o /tmp/harborops_roles_smoke.json -w "%{http_code}" -b "${COOKIE_JAR}" "${BASE_URL}/api/access/me/roles/")"
if [[ "${roles_code}" != "200" ]]; then
  echo "Role context smoke failed with status ${roles_code}" >&2
  exit 1
fi

echo "Running real write action"
request_ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
request_nonce="$(generate_nonce)"
signing_payload="POST"$'\n'"/api/auth/favorites/"$'\n'"${request_ts}"$'\n'"${request_nonce}"
session_signature="$(hmac_sha256_hex "${csrf_token}" "${signing_payload}")"
favorite_payload='{"kind":"trip","reference_id":"smoke-trip"}'
favorite_code="$(curl -sk -o /tmp/harborops_favorite_smoke.json -w "%{http_code}" -b "${COOKIE_JAR}" -H "Content-Type: application/json" -H "X-CSRFToken: ${csrf_token}" -H "Referer: ${BASE_URL}/" -H "X-Request-Timestamp: ${request_ts}" -H "X-Request-Nonce: ${request_nonce}" -H "X-Session-Signature: ${session_signature}" -X POST "${BASE_URL}/api/auth/favorites/" --data "${favorite_payload}")"
if [[ "${favorite_code}" != "201" && "${favorite_code}" != "409" ]]; then
  echo "Write-action smoke failed with status ${favorite_code}" >&2
  exit 1
fi

echo "Frontend-backend smoke test passed"
