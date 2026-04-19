#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

protected_dirs=(
  "${ROOT_DIR}/backend/media/verification_docs"
  "${ROOT_DIR}/backend/media/exports"
)

blocked=()
for directory in "${protected_dirs[@]}"; do
  [[ -d "${directory}" ]] || continue
  while IFS= read -r -d '' path; do
    rel="${path#${ROOT_DIR}/}"
    blocked+=("${rel}")
  done < <(find "${directory}" -type f ! -name ".gitkeep" -print0)
done

if [[ ${#blocked[@]} -gt 0 ]]; then
  echo "Sensitive runtime artifacts detected:" >&2
  for item in "${blocked[@]}"; do
    echo "- ${item}" >&2
  done
  exit 1
fi

echo "No sensitive runtime artifacts detected"
