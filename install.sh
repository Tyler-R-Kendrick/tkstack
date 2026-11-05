#!/usr/bin/env bash
# Install tkstack dotfiles.
# A checkout (this file beside scripts/bootstrap.py) installs that checkout.
# Any other invocation, including `curl | bash`, clones or updates
# ~/.local/share/tkstack and continues from there.
set -euo pipefail

checkout_root() {
  if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
    local root
    root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    if [[ -f "$root/scripts/bootstrap.py" ]]; then
      printf '%s\n' "$root"
      return 0
    fi
  fi
  return 1
}

if ! tkstack_root="$(checkout_root)"; then
  dest="${TKSTACK_HOME:-$HOME/.local/share/tkstack}"
  url="${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}"
  if [[ -d "$dest/.git" ]]; then
    git -C "$dest" pull --ff-only
  elif [[ -e "$dest" ]]; then
    printf '%s\n' "tkstack: $dest exists and is not a git checkout." >&2
    exit 1
  else
    mkdir -p -- "$(dirname -- "$dest")"
    git clone --depth 1 "$url" "$dest"
  fi
  exec "$dest/install.sh" "$@"
fi

tkstack_python=""
if [[ -n "${TKSTACK_PYTHON:-}" ]]; then
  tkstack_python="$TKSTACK_PYTHON"
else
  for candidate in python3 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      tkstack_python="$candidate"
      break
    fi
  done
fi
if [[ -z "$tkstack_python" ]] || ! command -v "$tkstack_python" >/dev/null 2>&1; then
  printf '%s\n' 'tkstack requires Python 3.11+; set TKSTACK_PYTHON to its executable.' >&2
  exit 1
fi
exec "$tkstack_python" -B "$tkstack_root/scripts/bootstrap.py" "$@"
