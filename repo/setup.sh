#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${ROOT_DIR}/deploy/bootstrap_env.sh"
docker compose -f "${ROOT_DIR}/docker-compose.yml" up --build "$@"
