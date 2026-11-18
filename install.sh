#!/usr/bin/env bash
# Install tkstack dotfiles.
# A checkout (this file beside scripts/install.py) installs that checkout.
# Any other invocation, including `curl | bash`, obtains
# ~/.local/share/tkstack and continues from there.
#
# The whole body is main(), called on the last line. A truncated download
# therefore defines functions and stops, instead of running a prefix.
#
# Resolve the current stable Python 3 when bootstrapping a missing interpreter.
PYTHON_VERSION=3

_archive=""
_extract=""

cleanup_downloads() {
  if [[ -n "${_archive}" ]]; then
    rm -f -- "$_archive"
    _archive=""
  fi
  if [[ -n "${_extract}" ]]; then
    rm -rf -- "$_extract"
    _extract=""
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
    if [[ -f "$root/scripts/install.py" ]]; then
      printf '%s\n' "$root"
      return 0
    fi
  fi
  return 1
}

tarball_url() {
  if [[ -n "${TKSTACK_TARBALL:-}" ]]; then
    case "$TKSTACK_TARBALL" in
      https://*)
        printf '%s\n' "$TKSTACK_TARBALL"
        return 0
        ;;
      *)
        printf '%s\n' 'tkstack: TKSTACK_TARBALL must be an https:// URL.' >&2
        return 1
        ;;
    esac
  fi
  if [[ ! "${TKSTACK_REV:-}" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' 'tkstack: supply a full TKSTACK_REV or an explicit HTTPS TKSTACK_TARBALL.' >&2
    return 1
  fi
  local repo
  repo="$(expected_repo)"
  if [[ "$repo" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'https://codeload.github.com/%s/%s/tar.gz/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "$TKSTACK_REV"
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
  if [[ ! "${TKSTACK_TARBALL_SHA256:-}" =~ ^[a-f0-9]{64}$ ]]; then
    printf '%s\n' 'tkstack: set TKSTACK_TARBALL_SHA256 to a separately trusted archive digest.' >&2
    exit 1
  fi
  archive="$(mktemp)"
  extract="$(mktemp -d)"
  _archive="$archive"
  _extract="$extract"
  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 0 -o "$archive" -- "$url"; then
    printf '%s\n' 'tkstack: downloading the repository tarball failed.' >&2
    exit 1
  fi
  if [[ "$(file_sha256 "$archive")" != "$TKSTACK_TARBALL_SHA256" ]]; then
    printf '%s\n' 'tkstack: repository archive sha256 mismatch.' >&2
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
  if [[ -z "$inner" || ! -f "$inner/install.sh" || ! -f "$inner/scripts/install.py" ]]; then
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
  local dest expected head changes
  dest="${TKSTACK_HOME:-$HOME/.local/share/tkstack}"
  expected="$(expected_repo)"
  if [[ -n "${TKSTACK_REV:-}" && ! "$TKSTACK_REV" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s\n' 'tkstack: TKSTACK_REV requires a full commit ID.' >&2
    exit 1
  fi
  if [[ -e "$dest" ]]; then
    if [[ ! -f "$dest/install.sh" || ! -f "$dest/scripts/install.py" ]]; then
      printf '%s\n' "tkstack: $dest exists and is not a tkstack checkout." >&2
      exit 1
    fi
    # A pre-existing directory was not created by this run. A receipt inside it
    # is self-attested. Run it only for a matching git origin, or when
    # TKSTACK_TRUST_HOME=1 names that consent explicitly.
    if git_origin_matches "$dest"; then
      if [[ -n "${TKSTACK_REV:-}" ]]; then
        if ! head="$(git -C "$dest" rev-parse HEAD)" || ! changes="$(git -C "$dest" status --porcelain)" ||
           [[ "$head" != "$TKSTACK_REV" || -n "$changes" ]]; then
          printf '%s\n' 'tkstack: choose a fresh TKSTACK_HOME for this pinned revision.' >&2
          exit 1
        fi
      elif ! git -C "$dest" pull --ff-only; then
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
    if [[ -d "$dest/.git" && -n "${TKSTACK_REV:-}" ]]; then
      printf '%s\n' 'tkstack: pinned checkout requires a matching Git origin.' >&2
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
    if [[ -n "${TKSTACK_REV:-}" ]]; then
      git init -q "$dest"
      git -C "$dest" remote add origin "$expected"
      git -C "$dest" fetch --depth 1 origin "$TKSTACK_REV"
      git -C "$dest" checkout --detach "$TKSTACK_REV"
    else
      git clone --depth 1 "${TKSTACK_REPO:-https://github.com/Tyler-R-Kendrick/tkstack.git}" "$dest"
    fi
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
  local bindir platform arch target asset url temporary archive checksum expected actual binary
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    printf '%s\n' 'tkstack needs curl to install uv when Python 3.11+ is missing.' >&2
    exit 1
  fi
  bindir="${HOME}/.local/bin"
  mkdir -p -- "$bindir"
  if [[ -x "$bindir/uv" ]]; then
    printf '%s\n' "$bindir/uv"
    return 0
  fi
  if [[ -e "$bindir/uv" || -L "$bindir/uv" ]]; then
    printf '%s\n' "tkstack: refusing to replace $bindir/uv." >&2
    return 1
  fi
  platform="$(uname -s)"
  arch="$(uname -m)"
  case "$arch" in x86_64|amd64) arch=x86_64 ;; aarch64|arm64) arch=aarch64 ;; *) printf '%s\n' 'tkstack: unsupported uv architecture.' >&2; return 1 ;; esac
  case "$platform" in Linux) target="${arch}-unknown-linux-gnu" ;; Darwin) target="${arch}-apple-darwin" ;; *) printf '%s\n' 'tkstack: unsupported uv platform.' >&2; return 1 ;; esac
  asset="uv-${target}.tar.gz"
  url="https://github.com/astral-sh/uv/releases/latest/download/$asset"
  temporary="$(mktemp -d)"
  archive="$temporary/$asset"
  checksum="$temporary/checksum"
  if ! curl -fsSL --proto '=https' --tlsv1.2 --retry 0 -o "$archive" -- "$url" ||
     ! curl -fsSL --proto '=https' --tlsv1.2 --retry 0 -o "$checksum" -- "$url.sha256"; then
    rm -rf -- "$temporary"
    printf '%s\n' 'tkstack: downloading the current uv release failed.' >&2
    return 1
  fi
  expected="$(awk 'NR==1 {print $1}' "$checksum")"
  actual="$(file_sha256 "$archive")"
  if [[ ! "$expected" =~ ^[a-f0-9]{64}$ || "$actual" != "$expected" ]]; then
    rm -rf -- "$temporary"
    printf '%s\n' 'tkstack: the uv release sha256 does not match.' >&2
    return 1
  fi
  binary="uv-${target}/uv"
  if ! tar -xzf "$archive" -C "$temporary" -- "$binary" || [[ ! -f "$temporary/$binary" || -L "$temporary/$binary" ]]; then
    rm -rf -- "$temporary"
    printf '%s\n' 'tkstack: the uv release has no regular executable.' >&2
    return 1
  fi
  cp -- "$temporary/$binary" "$bindir/uv"
  chmod 755 "$bindir/uv"
  rm -rf -- "$temporary"
  if [[ ! -x "$bindir/uv" ]]; then
    printf '%s\n' 'tkstack: could not install uv.' >&2
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
      exec "$TKSTACK_PYTHON" -B "$tkstack_root/scripts/install.py" "$@"
    fi
    printf '%s\n' 'tkstack: TKSTACK_PYTHON is not a usable Python 3.11+.' >&2
    exit 1
  fi
  for candidate in python3 python3.13 python3.12 python3.11; do
    if python_is_usable "$candidate"; then
      cleanup_downloads
      exec "$candidate" -B "$tkstack_root/scripts/install.py" "$@"
    fi
  done
  uv_bin="$(ensure_uv)"
  "$uv_bin" python install "$PYTHON_VERSION"
  cleanup_downloads
  exec "$uv_bin" run --python "$PYTHON_VERSION" --no-project -- python -B "$tkstack_root/scripts/install.py" "$@"
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
