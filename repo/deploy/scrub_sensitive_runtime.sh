#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

targets=(
  "${ROOT_DIR}/backend/media/verification_docs"
  "${ROOT_DIR}/backend/media/exports"
)

deleted=0
for target in "${targets[@]}"; do
  [[ -d "${target}" ]] || continue
  while IFS= read -r -d '' file; do
    rm -f -- "${file}"
    deleted=$((deleted + 1))
  done < <(find "${target}" -type f ! -name ".gitkeep" -print0)
  find "${target}" -mindepth 1 -type d -empty -delete 2>/dev/null || true
done

echo "Removed ${deleted} sensitive runtime files"
echo "Sensitive runtime artifact scrub complete"
