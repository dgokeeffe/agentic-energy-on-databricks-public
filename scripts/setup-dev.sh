#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

install_with_brew() {
  local command_name=$1
  local formula=$2

  if command -v "$command_name" >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v brew >/dev/null 2>&1; then
    printf 'Missing %s. Install Homebrew or install %s manually, then rerun make setup.\n' \
      "$command_name" "$formula" >&2
    exit 1
  fi
  printf 'Installing %s with Homebrew...\n' "$formula"
  HOMEBREW_NO_AUTO_UPDATE=1 brew install "$formula"
}

if ! command -v python3 >/dev/null 2>&1; then
  printf 'Missing python3. Install Python 3.10 or later, then rerun make setup.\n' >&2
  exit 1
fi

install_with_brew uv uv
install_with_brew gh gh
install_with_brew node node

printf 'Synchronising root Python environment...\n'
uv sync --frozen --extra test
printf 'Synchronising NEMWEB foundation environment...\n'
uv sync --project nemweb_foundation --frozen --extra test
printf 'Synchronising NEMWEB ML environment...\n'
uv sync --project nemweb_ml --frozen --extra test

printf 'Installing NEMWEB app dependencies...\n'
npm --prefix nemweb_app ci --include=dev

cat <<'EOF'

Development setup is ready.
Authentication is intentionally not automated. If needed, run:
  gh auth status
  databricks auth profiles
EOF
