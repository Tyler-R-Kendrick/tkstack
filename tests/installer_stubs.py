"""PATH and command stubs shared by the install.sh tests."""

import os
from pathlib import Path


def stub_path(root, hide_prefixes, stubs):
    """Build a PATH whose stub executables hide selected real commands."""
    root.mkdir(parents=True, exist_ok=True)
    bindir = root / "stubs"
    system = root / "system-bin"
    bindir.mkdir()
    system.mkdir()
    hidden = set()
    for name, text in stubs.items():
        path = bindir / name
        path.write_text(text)
        path.chmod(0o755)
        hidden.add(name)
    seen = set(hidden)
    for directory in os.environ["PATH"].split(os.pathsep):
        try:
            entries = list(Path(directory).iterdir())
        except OSError:
            continue
        for source in entries:
            name = source.name
            if name in seen or any(name == prefix or name.startswith(prefix) for prefix in hide_prefixes):
                continue
            if not source.is_file() or not os.access(source, os.X_OK):
                continue
            try:
                (system / name).symlink_to(source)
            except FileExistsError:
                continue
            seen.add(name)
    return str(bindir) + os.pathsep + str(system)


UV_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$UV_LOG"
exit 0
"""

UV_INSTALLER_BODY = """#!/bin/sh
bindir="${UV_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$bindir"
cat > "$bindir/uv" << 'UV'
#!/bin/sh
printf '%s\\n' "$*" >> "$UV_LOG"
exit 0
UV
chmod +x "$bindir/uv"
"""

CURL_UV = r"""#!/bin/sh
printf '%s\n' "$*" >> "$CURL_LOG"
out=
url=
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out=$2; shift 2 ;;
    -o*) out=${1#-o}; shift ;;
    https://*|http://*) url=$1; shift ;;
    *) shift ;;
  esac
done
case "$url" in
  https://astral.sh/uv/0.12.23/install.sh) ;;
  *) printf '%s\n' "unexpected url: $url" >&2; exit 1 ;;
esac
[ -n "$out" ] || { printf '%s\n' 'missing -o' >&2; exit 1; }
cat "$UV_INSTALLER_FILE" > "$out"
"""

CURL_TARBALL = r"""#!/bin/sh
printf '%s\n' "$*" >> "$CURL_LOG"
out=
url=
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out=$2; shift 2 ;;
    -o*) out=${1#-o}; shift ;;
    https://*|http://*) url=$1; shift ;;
    *) shift ;;
  esac
done
case "$url" in
  https://codeload.github.com/Tyler-R-Kendrick/tkstack/tar.gz/main) ;;
  *)
    if [ -n "${CURL_ACCEPT:-}" ] && [ "$url" = "$CURL_ACCEPT" ]; then
      :
    else
      printf '%s\n' "unexpected url: $url" >&2
      exit 1
    fi
    ;;
esac
[ -n "$out" ] || exit 1
if [ -n "${BAD_TAR:-}" ]; then
  cat "$BAD_TAR" > "$out"
  exit 0
fi
work=$(mktemp -d)
mkdir -p "$work/tkstack-main/scripts"
printf '%s\n' 'print(1)' > "$work/tkstack-main/scripts/install.py"
cat > "$work/tkstack-main/install.sh" << 'END'
#!/bin/sh
printf '%s\n' "local-install $*" >> "$INSTALL_LOG"
END
chmod +x "$work/tkstack-main/install.sh"
tar -czf "$out" -C "$work" tkstack-main
rm -rf "$work"
"""

GIT_CLONE_STUB = r"""#!/bin/sh
printf '%s\n' "$*" >> "$GIT_LOG"
if [ "$1" = -C ]; then
  shift 2
fi
if [ "$1" = clone ]; then
  for dest do :; done
  mkdir -p "$dest/scripts" "$dest/.git"
  printf '%s\n' 'print(1)' > "$dest/scripts/install.py"
  cat > "$dest/install.sh" << 'END_STUB'
#!/bin/sh
echo local-install "$*"
END_STUB
  chmod +x "$dest/install.sh"
fi
if [ "$1" = remote ]; then
  printf '%s\n' 'https://github.com/Tyler-R-Kendrick/tkstack.git'
fi
if [ "$1" = pull ]; then
  if [ -n "${GIT_PULL_STATUS:-}" ]; then
    exit "$GIT_PULL_STATUS"
  fi
fi
exit 0
"""

GIT_ORIGIN_STUB = r"""#!/bin/sh
printf '%s\n' "$*" >> "$GIT_LOG"
if [ "$1" = -C ]; then shift 2; fi
if [ "$1" = remote ]; then printf '%s\n' "$GIT_ORIGIN"; fi
if [ "$1" = pull ]; then exit 0; fi
exit 0
"""
