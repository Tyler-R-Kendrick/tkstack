#!/usr/bin/env bash
# Install tkstack dotfiles.
# A checkout (this file beside scripts/bootstrap.py) installs that checkout.
# Any other invocation, including `curl | bash`, obtains
# ~/.local/share/tkstack and continues from there. Git clones when it is on
# PATH; otherwise curl downloads the GitHub tarball.
# Bash and curl are the host prerequisites. Missing Python 3.11+ is installed
# with the official uv installer, then `uv python install 3.12`.
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

tarball_url() {
  if [[ -n "${TKSTACK_TARBALL:-}" ]]; then
    printf '%s\n' "$TKSTACK_TARBALL"
    return 0
  fi
  local repo
  repo="${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}"
  repo="${repo%.git}"
  if [[ "$repo" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'https://codeload.github.com/%s/%s/tar.gz/main\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi
  printf '%s\n' 'tkstack: git is not on PATH, and TKSTACK_REPO is not a GitHub HTTPS URL. Install git or set TKSTACK_TARBALL.' >&2
  return 1
}

download_tarball() {
  local dest url archive extract inner candidate
  dest="$1"
  url="$(tarball_url)"
  archive="$(mktemp)"
  extract="$(mktemp -d)"
  curl -fsSL "$url" -o "$archive"
  tar -xzf "$archive" -C "$extract"
  inner=""
  for candidate in "$extract"/*; do
    if [[ -d "$candidate" ]]; then
      inner="$candidate"
      break
    fi
  done
  if [[ -z "$inner" || ! -f "$inner/install.sh" || ! -f "$inner/scripts/bootstrap.py" ]]; then
    rm -rf -- "$extract"
    rm -f -- "$archive"
    printf '%s\n' 'tkstack: the downloaded archive is not a tkstack checkout.' >&2
    exit 1
  fi
  mkdir -p -- "$(dirname -- "$dest")"
  mv -- "$inner" "$dest"
  rm -rf -- "$extract"
  rm -f -- "$archive"
}

fetch_checkout() {
  local dest url
  dest="${TKSTACK_HOME:-$HOME/.local/share/tkstack}"
  url="${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}"
  if [[ -f "$dest/install.sh" && -f "$dest/scripts/bootstrap.py" ]]; then
    if [[ -d "$dest/.git" ]] && command -v git >/dev/null 2>&1; then
      git -C "$dest" pull --ff-only
    elif [[ -d "$dest/.git" ]]; then
      printf '%s\n' "tkstack: git is not on PATH; using the existing checkout at $dest." >&2
    fi
    exec "$dest/install.sh" "$@"
  fi
  if [[ -e "$dest" ]]; then
    printf '%s\n' "tkstack: $dest exists and is not a tkstack checkout." >&2
    exit 1
  fi
  mkdir -p -- "$(dirname -- "$dest")"
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 "$url" "$dest"
  else
    if ! command -v curl >/dev/null 2>&1; then
      printf '%s\n' 'tkstack needs git or curl to download the repository.' >&2
      exit 1
    fi
    download_tarball "$dest"
  fi
  exec "$dest/install.sh" "$@"
}

python_is_usable() {
  local candidate
  candidate="$1"
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]] || return 1
  elif ! command -v "$candidate" >/dev/null 2>&1; then
    return 1
  fi
  "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    printf '%s\n' 'tkstack needs curl to install uv when Python 3.11+ is missing.' >&2
    exit 1
  fi
  local bindir
  bindir="${UV_INSTALL_DIR:-$HOME/.local/bin}"
  mkdir -p -- "$bindir"
  # UV_INSTALL_DIR is the official installer's flat binary directory.
  # UV_NO_MODIFY_PATH keeps this bootstrap from editing shell startup files.
  curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$bindir" UV_NO_MODIFY_PATH=1 sh
  case ":$PATH:" in
    *":$bindir:"*) ;;
    *) PATH="$bindir:$PATH" ;;
  esac
  export PATH
  if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'tkstack: the uv installer did not put uv on PATH.' >&2
    exit 1
  fi
}

run_bootstrap() {
  local candidate
  if [[ -n "${TKSTACK_PYTHON:-}" ]]; then
    if python_is_usable "$TKSTACK_PYTHON"; then
      exec "$TKSTACK_PYTHON" -B "$tkstack_root/scripts/bootstrap.py" "$@"
    fi
    printf '%s\n' 'tkstack: TKSTACK_PYTHON is not a usable Python 3.11+.' >&2
    exit 1
  fi
  for candidate in python3 python3.13 python3.12 python3.11; do
    if python_is_usable "$candidate"; then
      exec "$candidate" -B "$tkstack_root/scripts/bootstrap.py" "$@"
    fi
  done
  ensure_uv
  uv python install 3.12
  exec uv run --python 3.12 --no-project -- python -B "$tkstack_root/scripts/bootstrap.py" "$@"
}

if ! tkstack_root="$(checkout_root)"; then
  fetch_checkout "$@"
fi
run_bootstrap "$@"
