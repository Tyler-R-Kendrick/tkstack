#!/usr/bin/env bash
set -euo pipefail
tkstack_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec "$tkstack_root/install.sh" --profile codex-cloud --offline "$@"
