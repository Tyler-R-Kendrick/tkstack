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
  # TKSTACK_TARBALL must be https. This script cannot hash its own archive:
  # tar.gz/main is a mutable ref, and an https URL only protects the transport.
  if [[ -n "${TKSTACK_TARBALL:-}" ]]; then
    case "$TKSTACK_TARBALL" in
      https://*)
        printf '%s\n' "$TKSTACK_TARBALL"
        return 0
        ;;
      *)
        printf '%s\n' 'tkstack: TKSTACK_TARBALL must be an https:// URL. The archive has no content hash; HTTPS does not pin the bytes.' >&2
        return 1
        ;;
    esac
  fi
  local repo
  repo="$(expected_repo)"
  if [[ "$repo" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'https://codeload.github.com/%s/%s/tar.gz/main\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi
  printf '%s\n' 'tkstack: git is not on PATH, and TKSTACK_REPO is not a GitHub HTTPS URL. Install git or set TKSTACK_TARBALL to an https:// archive.' >&2
  return 1
}

# Print the canonical absolute path of an absolute path. Follows symlinks.
# Missing trailing components are collapsed logically, so a broken link still
# resolves. Fails closed when readlink fails or a link loops. Does not use
# realpath, which is not required on the host.
canonicalize_path() {
  local input="$1"
  local -a parts=()
  local remaining component sofar target prefix depth=0
  case "$input" in
    /*) remaining="$input" ;;
    *) return 1 ;;
  esac
  if ! command -v readlink >/dev/null 2>&1; then
    return 1
  fi
  while [[ -n "$remaining" ]]; do
    while [[ "$remaining" == /* ]]; do
      remaining="${remaining#/}"
    done
    [[ -n "$remaining" ]] || break
    component="${remaining%%/*}"
    if [[ "$remaining" == */* ]]; then
      remaining="${remaining#*/}"
    else
      remaining=""
    fi
    case "$component" in
      ""|.) continue ;;
      ..)
        if ((${#parts[@]} > 0)); then
          unset 'parts[${#parts[@]}-1]'
        fi
        continue
        ;;
    esac
    parts+=("$component")
    if ((${#parts[@]} == 0)); then
      sofar="/"
    else
      prefix="$(IFS=/; printf '%s' "${parts[*]}")"
      sofar="/$prefix"
    fi
    if [[ -L "$sofar" ]]; then
      # An empty readlink result is not a resolved path. Fail closed.
      if ! target="$(readlink -- "$sofar")" || [[ -z "$target" ]]; then
        return 1
      fi
      unset 'parts[${#parts[@]}-1]'
      depth=$((depth + 1))
      if ((depth > 40)); then
        return 1
      fi
      if [[ "$target" == /* ]]; then
        parts=()
      fi
      if [[ -n "$remaining" ]]; then
        remaining="${target}/${remaining}"
      else
        remaining="$target"
      fi
    fi
  done
  if ((${#parts[@]} == 0)); then
    printf '/\n'
  else
    prefix="$(IFS=/; printf '%s' "${parts[*]}")"
    printf '/%s\n' "$prefix"
  fi
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

# List symlinks without following them. Bash only: find is not a host prerequisite.
_list_symlinks_walk() {
  local dir="$1" entry
  [[ -d "$dir" && ! -L "$dir" ]] || return 0
  if [[ ! -r "$dir" || ! -x "$dir" ]]; then
    return 1
  fi
  for entry in "$dir"/*; do
    if [[ -L "$entry" ]]; then
      printf '%s\n' "$entry"
    elif [[ -d "$entry" ]]; then
      _list_symlinks_walk "$entry" || return 1
    fi
  done
}

list_symlinks() {
  local nullglob=0 dotglob=0 status
  shopt -q nullglob && nullglob=1
  shopt -q dotglob && dotglob=1
  shopt -s nullglob dotglob
  _list_symlinks_walk "$1"
  status=$?
  if ((nullglob == 0)); then
    shopt -u nullglob
  fi
  if ((dotglob == 0)); then
    shopt -u dotglob
  fi
  return "$status"
}

reject_escaping_links() {
  local root="$1" root_real link resolved listing
  if ! root_real="$(canonicalize_path "$root")"; then
    printf '%s\n' 'tkstack: cannot canonicalize the extract directory; refusing the archive.' >&2
    return 1
  fi
  if [[ -z "$root_real" || "$root_real" != /* ]]; then
    printf '%s\n' 'tkstack: cannot canonicalize the extract directory; refusing the archive.' >&2
    return 1
  fi
  if ! listing="$(list_symlinks "$root")"; then
    printf '%s\n' 'tkstack: cannot list archive symlinks; refusing the archive.' >&2
    return 1
  fi
  while IFS= read -r link; do
    [[ -n "$link" ]] || continue
    if ! resolved="$(canonicalize_path "$link")"; then
      printf '%s\n' "tkstack: cannot canonicalize archive symlink: $link" >&2
      return 1
    fi
    case "$resolved" in
      "$root_real"|"$root_real"/*) ;;
      *)
        printf '%s\n' "tkstack: the archive symlink escapes the extract directory: $link" >&2
        return 1
        ;;
    esac
  done <<< "$listing"
}

write_receipt() {
  local dest="$1" url="$2" repo
  repo="$(expected_repo)"
  mkdir -p -- "$dest/.tkstack"
  printf 'kind=tarball\nrepo=%s\nurl=%s\n' "$repo" "$url" > "$dest/.tkstack/source-receipt.txt"
}

download_tarball() {
  local dest="$1" replacing="${2:-}" url archive extract inner candidate
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
  # Copy preserved state into the new tree before the live directory moves.
  # The copy is not on the EXIT trap. A failed swap puts the old directory back.
  if [[ "$replacing" == replace && -e "$dest/.tkstack" ]]; then
    if [[ -L "$dest/.tkstack" || ! -d "$dest/.tkstack" ]]; then
      printf '%s\n' 'tkstack: refusing to replace a checkout whose .tkstack entry is not a real directory.' >&2
      exit 1
    fi
    rm -rf -- "$inner/.tkstack"
    if ! cp -a -- "$dest/.tkstack" "$inner/.tkstack"; then
      printf '%s\n' 'tkstack: could not preserve .tkstack; leaving the existing checkout in place.' >&2
      exit 1
    fi
  fi
  local stage_root="" backup_root="" backup=""
  stage_root="$(mktemp -d)"
  if ! mv -- "$inner" "$stage_root/tree"; then
    rm -rf -- "$stage_root"
    printf '%s\n' 'tkstack: could not stage the downloaded checkout.' >&2
    exit 1
  fi
  inner="$stage_root/tree"
  mkdir -p -- "$(dirname -- "$dest")"
  if [[ -e "$dest" ]]; then
    backup_root="$(mktemp -d)"
    backup="$backup_root/previous"
    if ! mv -- "$dest" "$backup"; then
      rm -rf -- "$stage_root" "$backup_root"
      printf '%s\n' 'tkstack: could not move the existing checkout aside; leaving it in place.' >&2
      exit 1
    fi
  fi
  # Plain mv: dest was just moved aside. mv -T is GNU-only and breaks macOS.
  if [[ -e "$dest" ]] || ! mv -- "$inner" "$dest"; then
    if [[ -n "$backup" && -e "$backup" && ! -e "$dest" ]]; then
      mv -- "$backup" "$dest" || true
    fi
    rm -rf -- "$stage_root"
    if [[ -n "$backup_root" ]]; then
      rm -rf -- "$backup_root"
    fi
    printf '%s\n' 'tkstack: could not install the downloaded checkout; restored the previous directory.' >&2
    exit 1
  fi
  if [[ -n "$backup_root" ]]; then
    rm -rf -- "$backup_root"
  fi
  rm -rf -- "$stage_root"
  write_receipt "$dest" "$url"
  cleanup_downloads
}

git_origin_matches() {
  local dest="$1" origin
  if [[ ! -d "$dest/.git" ]]; then
    return 1
  fi
  if ! command -v git >/dev/null 2>&1; then
    return 1
  fi
  if ! origin="$(git -C "$dest" remote get-url origin 2>/dev/null)"; then
    return 1
  fi
  [[ "$(normalize_repo "$origin")" == "$(expected_repo)" ]]
}

fetch_checkout() {
  local dest expected
  dest="${TKSTACK_HOME:-$HOME/.local/share/tkstack}"
  expected="$(expected_repo)"
  if [[ -e "$dest" ]]; then
    if [[ ! -f "$dest/install.sh" || ! -f "$dest/scripts/bootstrap.py" ]]; then
      printf '%s\n' "tkstack: $dest exists and is not a tkstack checkout." >&2
      exit 1
    fi
    # A pre-existing directory was not created by this run. A receipt inside it
    # is self-attested. Run it only for a matching git origin, or when
    # TKSTACK_TRUST_HOME=1 names that consent explicitly.
    if git_origin_matches "$dest"; then
      if ! git -C "$dest" pull --ff-only; then
        printf '%s\n' "tkstack: git pull --ff-only failed in $dest. Commit or stash local changes so a fast-forward can succeed, then run the installer again." >&2
        exit 1
      fi
      cleanup_downloads
      exec "$dest/install.sh" "$@"
    fi
    if [[ "${TKSTACK_TRUST_HOME:-}" != 1 ]]; then
      printf '%s\n' "tkstack: $dest already exists and this installer run did not create it. Refusing to run it. Set TKSTACK_TRUST_HOME=1 to use a pre-existing checkout, or use one whose git origin matches $expected." >&2
      exit 1
    fi
    if [[ -d "$dest/.git" ]]; then
      printf '%s\n' "tkstack: TKSTACK_TRUST_HOME=1; running the pre-existing git checkout at $dest without pulling, because its origin does not match $expected." >&2
      cleanup_downloads
      exec "$dest/install.sh" "$@"
    fi
    printf '%s\n' "tkstack: $dest is a tarball checkout. It stays frozen between runs because there is no git fast-forward. This run downloads it again; fixes arrive only when the installer runs." >&2
    download_tarball "$dest" replace
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
  # The installer's stdout must not mix with the path this function prints.
  if ! UV_INSTALL_DIR="$bindir" UV_NO_MODIFY_PATH=1 sh "$installer" >&2; then
    printf '%s\n' 'tkstack: the uv installer failed.' >&2
    exit 1
  fi
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
