#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in uv node npm; do
  command -v "$tool" >/dev/null || { echo "Install $tool, then rerun make setup." >&2; exit 1; }
done
uv sync --frozen --extra test
npm --prefix app ci --ignore-scripts --legacy-peer-deps
