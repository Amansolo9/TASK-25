#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${ROOT_DIR}/.tmp/frontend_verification/${STAMP}"

mkdir -p "${OUT_DIR}"

echo "[1/3] npm ci"
npm --prefix "${FRONTEND_DIR}" ci | tee "${OUT_DIR}/npm-ci.log"

echo "[2/3] npm run test:run"
npm --prefix "${FRONTEND_DIR}" run test:run | tee "${OUT_DIR}/npm-test-run.log"

echo "[3/3] npm run build"
npm --prefix "${FRONTEND_DIR}" run build | tee "${OUT_DIR}/npm-build.log"

echo "Frontend verification logs: ${OUT_DIR}"
