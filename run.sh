#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"


# Try local venv first, then workspace-level venv.
if [[ -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.venv/bin/activate"
elif [[ -f "$SCRIPT_DIR/../.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/../.venv/bin/activate"
fi

HOST="${APP_HOST:-127.0.0.1}"
PORT="${APP_PORT:-8000}"

exec uvicorn main:app --host "$HOST" --port "$PORT"
