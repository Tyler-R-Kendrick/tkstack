#!/usr/bin/env bash
set -euo pipefail

tkstack_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
tkstack_python="${TKSTACK_PYTHON:-python3}"
if ! command -v "$tkstack_python" >/dev/null 2>&1; then
  printf '%s\n' 'tkstack requires Python 3.11+; set TKSTACK_PYTHON to its executable.' >&2
  exit 1
fi
exec "$tkstack_python" -B "$tkstack_root/scripts/bootstrap.py" "$@"
