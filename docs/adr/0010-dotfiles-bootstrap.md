# 0010: One reproducible dotfiles bootstrap for hosts and environment hooks

Status: accepted, 2026-10-30.

The user clarified that this repository must provision its complete setup as
agent dotfiles, including devcontainer and Codex cloud startup. Existing narrow
installers alone required manual sequencing and left runtime/state setup separate.

Add a root `install.sh` that delegates to a standard-library Python coordinator.
Profiles select normal user dotfiles, devcontainers, or Codex-only cloud hosts.
The coordinator reuses source verification, link/config installers, state
renderers, runtime installers, and doctor instead of implementing their work again.
Independent runtime installers run with bounded workers; configuration has one
writer after they join. Failures are collected and feasible work continues.
An OS advisory lock protects shared checkout setup and releases on process death.

Toolchains install privately when needed: hash-locked uv and checksum-verified
Node archives. Graphify and Headroom use hash-locked Python recipes; OpenWiki
uses its npm lock; release executables retain their existing source digest pins.
Private command shims and launcher environment resolution make these tools usable
beyond the bootstrap process without changing provider/authentication variables.
Owned Bash/login source blocks preserve foreign content. Conflicting/symlinked
shell managers can use explicit no-shell integration and source the generated file.

Home is the default target. Actual home installs honor CODEX_HOME and
TKSTACK_USER_DIR; isolated/project targets remain inside their selected locations.
Runtime caches, session logs, reports, and state policies live in `.tkstack`.
Source history is not copied into a fresh user's learning ledger.

First-create/setup hooks provision software; repeated startup can use offline
mode. Read-only check/dry-run modes initialize nothing. Optional strict mode fails
on known unresolved local prerequisites; unknown host OAuth state is reported
without pretending to authenticate. No model/indexing job, service/proxy routing,
Copilot automation, account login, or remote environment API update is implied.

Include a runnable devcontainer definition and Codex setup/startup wrappers.
Their remote-clone examples require a published revision containing these files.
Source mounts/checkouts remain durable because installed links reference them.
Verification covers a fresh public source copy with no cached state, repeat runs,
path spaces, preservation/drift, checksum/traversal failures, scoped roots, custom
Codex home selection, concurrent failure handling, and lock release after death.
