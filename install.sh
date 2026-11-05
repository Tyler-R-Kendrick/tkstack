#!/usr/bin/env bash
# Install tkstack dotfiles.
# A checkout (this file beside scripts/bootstrap.py) installs that checkout.
# Any other invocation, including `curl | bash`, obtains
# ~/.local/share/tkstack and continues from there.
#
# The whole body is main(), called on the last line. A truncated download
# therefore defines functions and stops, instead of running a prefix.
#
# uv pin rotation: change UV_VERSION, UV_INSTALLER_URL, UV_INSTALLER_SHA256,
# and PYTHON_VERSION together. uv 0.12.23 can install CPython 3.12.15.
# It does not ship 3.12.16. The installer sha256 is for that version's
# install.sh (astral.sh and the GitHub release asset match).

UV_VERSION=0.12.23
UV_INSTALLER_URL="https://astral.sh/uv/${UV_VERSION}/install.sh"
UV_INSTALLER_SHA256=b8e6c43099ee9f9a550984d3ad56948457c689e7a99c090b35377234ac241491
PYTHON_VERSION=3.12.15

_archive=""
_extract=""
_state=""
_uv_installer=""

cleanup_downloads() {
  if [[ -n "${_archive}" ]]; then
    rm -f -- "$_archive"
    _archive=""
  fi
  if [[ -n "${_extract}" ]]; then
    rm -rf -- "$_extract"
    _extract=""
  fi
  if [[ -n "${_state}" ]]; then
    rm -rf -- "$_state"
    _state=""
  fi
  if [[ -n "${_uv_installer}" ]]; then
    rm -f -- "$_uv_installer"
    _uv_installer=""
  fi
}

normalize_repo() {
  local repo="$1"
  repo="${repo%.git}"
  repo="${repo%/}"
  printf '%s\n' "$repo"
}

expected_repo() {
  normalize_repo "${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}"
}

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
  repo="$(expected_repo)"
  if [[ "$repo" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'https://codeload.github.com/%s/%s/tar.gz/main\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi
  printf '%s\n' 'tkstack: git is not on PATH, and TKSTACK_REPO is not a GitHub HTTPS URL. Install git or set TKSTACK_TARBALL.' >&2
  return 1
}

reject_archive_members() {
  local archive="$1" listing member stripped part top first
  local -a parts
  if ! listing="$(tar -tzf "$archive" 2>/dev/null)"; then
    printf '%s\n' 'tkstack: the download is not a readable tar archive.' >&2
    return 1
  fi
  if [[ -z "$listing" ]]; then
    printf '%s\n' 'tkstack: the archive is empty.' >&2
    return 1
  fi
  top=""
  while IFS= read -r member; do
    if [[ -z "$member" ]]; then
      printf '%s\n' 'tkstack: the archive has an empty member.' >&2
      return 1
    fi
    case "$member" in
      /*|*//*)
        printf '%s\n' "tkstack: the archive member escapes the extract directory: $member" >&2
        return 1
        ;;
    esac
    stripped="${member%/}"
    IFS=/ read -r -a parts <<< "$stripped"
    for part in "${parts[@]}"; do
      if [[ -z "$part" || "$part" == "." || "$part" == ".." ]]; then
        printf '%s\n' "tkstack: the archive member escapes the extract directory: $member" >&2
        return 1
      fi
    done
    first="${parts[0]}"
    if [[ -z "$top" ]]; then
      top="$first"
    elif [[ "$first" != "$top" ]]; then
      printf '%s\n' 'tkstack: the archive has more than one top-level entry.' >&2
      return 1
    fi
  done <<< "$listing"
}

reject_escaping_links() {
  local root="$1" root_real link resolved
  root_real="$(realpath -m -- "$root")"
  while IFS= read -r link; do
    resolved="$(realpath -m -- "$link")"
    case "$resolved" in
      "$root_real"|"$root_real"/*) ;;
      *)
        printf '%s\n' "tkstack: the archive symlink escapes the extract directory: $link" >&2
        return 1
        ;;
    esac
  done < <(find "$root" -type l -print)
}

write_receipt() {
  local dest="$1" url="$2" repo
  repo="$(expected_repo)"
  mkdir -p -- "$dest/.tkstack"
  printf 'kind=tarball\nrepo=%s\nurl=%s\n' "$repo" "$url" > "$dest/.tkstack/source-receipt.txt"
}

download_tarball() {
  local dest="$1" replacing="${2:-}" url archive extract inner candidate saved
  url="$(tarball_url)"
  archive="$(mktemp)"
  extract="$(mktemp -d)"
  _archive="$archive"
  _extract="$extract"
  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 0 -o "$archive" -- "$url"; then
    printf '%s\n' 'tkstack: downloading the repository tarball failed.' >&2
    exit 1
  fi
  if ! reject_archive_members "$archive"; then
    exit 1
  fi
  if ! tar -xzf "$archive" -C "$extract" --no-same-owner --no-same-permissions; then
    printf '%s\n' 'tkstack: extracting the repository tarball failed.' >&2
    exit 1
  fi
  if ! reject_escaping_links "$extract"; then
    exit 1
  fi
  inner=""
  for candidate in "$extract"/*; do
    if [[ -d "$candidate" && ! -L "$candidate" ]]; then
      if [[ -n "$inner" ]]; then
        printf '%s\n' 'tkstack: the archive has more than one top-level entry.' >&2
        exit 1
      fi
      inner="$candidate"
    elif [[ -e "$candidate" || -L "$candidate" ]]; then
      printf '%s\n' 'tkstack: the archive has more than one top-level entry.' >&2
      exit 1
    fi
  done
  if [[ -z "$inner" || ! -f "$inner/install.sh" || ! -f "$inner/scripts/bootstrap.py" ]]; then
    printf '%s\n' 'tkstack: the downloaded archive is not a tkstack checkout.' >&2
    exit 1
  fi
  saved=""
  if [[ "$replacing" == replace && -d "$dest/.tkstack" ]]; then
    saved="$(mktemp -d)"
    _state="$saved"
    mv -- "$dest/.tkstack" "$saved/saved-state"
  fi
  if [[ -e "$dest" ]]; then
    rm -rf -- "$dest"
  fi
  mkdir -p -- "$(dirname -- "$dest")"
  mv -T -- "$inner" "$dest"
  if [[ -n "$saved" && -d "$saved/saved-state" ]]; then
    rm -rf -- "$dest/.tkstack"
    mv -- "$saved/saved-state" "$dest/.tkstack"
    rm -rf -- "$saved"
    _state=""
  fi
  write_receipt "$dest" "$url"
  cleanup_downloads
}

checkout_matches() {
  local dest="$1" expected origin receipt kind repo url want
  expected="$(expected_repo)"
  if [[ -d "$dest/.git" ]]; then
    if ! command -v git >/dev/null 2>&1; then
      printf '%s\n' "tkstack: $dest is a git checkout but git is not on PATH, so its remote cannot be verified." >&2
      return 1
    fi
    if ! origin="$(git -C "$dest" remote get-url origin 2>/dev/null)"; then
      printf '%s\n' "tkstack: $dest has no origin remote; refusing to run it." >&2
      return 1
    fi
    if [[ "$(normalize_repo "$origin")" != "$expected" ]]; then
      printf '%s\n' "tkstack: $dest origin does not match $expected; refusing to run it." >&2
      return 1
    fi
    return 0
  fi
  receipt="$dest/.tkstack/source-receipt.txt"
  if [[ ! -f "$receipt" ]]; then
    printf '%s\n' "tkstack: $dest is not a verified tkstack checkout. Refusing to run it." >&2
    return 1
  fi
  kind="$(awk -F= '$1=="kind"{print substr($0, index($0, "=") + 1)}' "$receipt")"
  repo="$(awk -F= '$1=="repo"{print substr($0, index($0, "=") + 1)}' "$receipt")"
  url="$(awk -F= '$1=="url"{print substr($0, index($0, "=") + 1)}' "$receipt")"
  want="$(tarball_url)"
  if [[ "$kind" != "tarball" || "$(normalize_repo "$repo")" != "$expected" || "$url" != "$want" ]]; then
    printf '%s\n' "tkstack: $dest tarball receipt does not match the expected repository; refusing to run it." >&2
    return 1
  fi
  return 0
}

fetch_checkout() {
  local dest
  dest="${TKSTACK_HOME:-$HOME/.local/share/tkstack}"
  if [[ -e "$dest" ]]; then
    if [[ ! -f "$dest/install.sh" || ! -f "$dest/scripts/bootstrap.py" ]]; then
      printf '%s\n' "tkstack: $dest exists and is not a tkstack checkout." >&2
      exit 1
    fi
    if ! checkout_matches "$dest"; then
      exit 1
    fi
    if [[ -d "$dest/.git" ]]; then
      if ! git -C "$dest" pull --ff-only; then
        printf '%s\n' "tkstack: git pull --ff-only failed in $dest. Commit or stash local changes so a fast-forward can succeed, then run the installer again." >&2
        exit 1
      fi
    else
      printf '%s\n' "tkstack: $dest is a tarball checkout. It stays frozen between runs because there is no git fast-forward. This run downloads it again; fixes arrive only when the installer runs." >&2
      download_tarball "$dest" replace
    fi
    cleanup_downloads
    exec "$dest/install.sh" "$@"
  fi
  mkdir -p -- "$(dirname -- "$dest")"
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 "${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}" "$dest"
  else
    if ! command -v curl >/dev/null 2>&1; then
      printf '%s\n' 'tkstack needs git or curl to download the repository.' >&2
      exit 1
    fi
    download_tarball "$dest"
  fi
  cleanup_downloads
  exec "$dest/install.sh" "$@"
}

python_is_usable() {
  local candidate="$1"
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]] || return 1
  elif ! command -v "$candidate" >/dev/null 2>&1; then
    return 1
  fi
  "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
}

file_sha256() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -- "$file" | awk 'NR==1 { print $1 }'
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -- "$file" | awk 'NR==1 { print $1 }'
    return 0
  fi
  printf '%s\n' 'tkstack: need sha256sum or shasum to verify the uv installer.' >&2
  exit 1
}

ensure_uv() {
  local existing bindir installer actual
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    printf '%s\n' 'tkstack needs curl to install uv when Python 3.11+ is missing.' >&2
    exit 1
  fi
  # Ignore a caller-supplied UV_INSTALL_DIR. Install into this home and exec
  # that absolute path. Do not prepend PATH.
  bindir="${HOME}/.local/bin"
  mkdir -p -- "$bindir"
  installer="$(mktemp)"
  _uv_installer="$installer"
  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 0 -o "$installer" -- "$UV_INSTALLER_URL"; then
    printf '%s\n' 'tkstack: downloading the uv installer failed.' >&2
    exit 1
  fi
  actual="$(file_sha256 "$installer")"
  if [[ "$actual" != "$UV_INSTALLER_SHA256" ]]; then
    printf '%s\n' 'tkstack: the uv installer sha256 does not match the pin.' >&2
    exit 1
  fi
  UV_INSTALL_DIR="$bindir" UV_NO_MODIFY_PATH=1 sh "$installer"
  rm -f -- "$installer"
  _uv_installer=""
  if [[ ! -x "$bindir/uv" ]]; then
    printf '%s\n' 'tkstack: the uv installer did not install uv.' >&2
    exit 1
  fi
  printf '%s\n' "$bindir/uv"
}

run_bootstrap() {
  local tkstack_root="$1"
  shift
  local candidate uv_bin
  if [[ -n "${TKSTACK_PYTHON:-}" ]]; then
    if python_is_usable "$TKSTACK_PYTHON"; then
      cleanup_downloads
      exec "$TKSTACK_PYTHON" -B "$tkstack_root/scripts/bootstrap.py" "$@"
    fi
    printf '%s\n' 'tkstack: TKSTACK_PYTHON is not a usable Python 3.11+.' >&2
    exit 1
  fi
  for candidate in python3 python3.13 python3.12 python3.11; do
    if python_is_usable "$candidate"; then
      cleanup_downloads
      exec "$candidate" -B "$tkstack_root/scripts/bootstrap.py" "$@"
    fi
  done
  uv_bin="$(ensure_uv)"
  "$uv_bin" python install "$PYTHON_VERSION"
  cleanup_downloads
  exec "$uv_bin" run --python "$PYTHON_VERSION" --no-project -- python -B "$tkstack_root/scripts/bootstrap.py" "$@"
}

main() {
  set -euo pipefail
  trap cleanup_downloads EXIT
  local tkstack_root
  if ! tkstack_root="$(checkout_root)"; then
    fetch_checkout "$@"
  fi
  run_bootstrap "$tkstack_root" "$@"
}

main "$@"
