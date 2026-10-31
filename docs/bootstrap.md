# Bootstrap agent dotfiles

Run the root script from a durable checkout containing this implementation.
Publish that revision before using the remote-clone examples below. It is noninteractive, works from
another directory, preserves existing settings, and can run again on startup:

```sh
git clone https://github.com/Tyler-R-Kendrick/tkstack.git "$HOME/.local/share/tkstack"
"$HOME/.local/share/tkstack/install.sh"
```

The default target is the current user's home. It installs Codex, Claude Code,
and Cursor skills/agents/rules, initializes ignored state, installs all declared
automatic runtimes, applies native hooks/MCP settings, initializes Lever's Copilot
layout in the source checkout, and verifies the result. Keep the checkout:
installed links, launchers, and runtime recipes refer to it. Moving it requires
re-running setup and handling any existing links owned by the old checkout.

## Profiles and commands

| Profile | Host configuration | Native Lever Copilot layout |
| --- | --- | --- |
| `dotfiles` (default) | Codex, Claude Code, Cursor in the selected home | Selected workspace; defaults to this checkout |
| `devcontainer` | Same host configuration | Selected workspace |
| `codex-cloud` | Codex only | Off; Lever remains available as a Codex skill |

```sh
./install.sh --profile devcontainer --workspace /workspaces/project
./install.sh --profile codex-cloud --workspace /workspace/project
./install.sh --target /repo --scope project --workspace /repo
./install.sh --offline                 # reapply cached/file configuration; no downloads
./install.sh --check                   # verify without changing files
./install.sh --dry-run                 # inspect plan/preflight without changing files
./install.sh --strict                  # fail for known unresolved manual prerequisites too
```

`--harness` and `--runtime` are repeatable selections. `--jobs 1..8` bounds
independent runtime installations (default 4); `--runtime-timeout 10..1800`
sets their process-group deadline (default 900 seconds). Runtime failures are
reported individually, remaining workers finish, and feasible file/configuration
work still runs. Failure exits 1; usage errors exit 2. Normal success exits 0.

`--copilot`/`--no-copilot` override the profile's native project layout.
`--no-toolchains` uses only available language/package tooling. `--no-shell`
keeps startup files untouched and still generates the command environment.
`--offline` explicitly accepts deferred missing runtimes while reporting them;
`--strict --offline` requires the locally observable prerequisites to be complete.
`--check` and `--dry-run` perform no initialization, downloads, or report writes.

`--scope home` is the default even for an alternative home-like `--target`.
Use `--scope project` explicitly for a repository installation. Workspace state
and optional Copilot files use `--workspace`, otherwise the source checkout;
setup does not guess another project's location from its working directory.
For real home installs, `CODEX_HOME` selects Codex's AGENTS/hooks/config location.
The real user state root also honors TKSTACK_USER_DIR. Isolated alternative
targets and project installs do not follow those variables
into another user's configuration. Existing provider/model/auth settings survive.

## Devcontainers

This checkout includes [`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json):
Python 3.12 image, Node 24 feature, first-create full setup, and offline repeated
startup. Its remote PATH includes the checkout's managed command directory.
The image/features are development environment inputs; local plugin/runtime
versions come from the repository's own locks.

To use tkstack as VS Code dotfiles for other devcontainers, set these **user**
settings:

```json
{
  "dotfiles.repository": "Tyler-R-Kendrick/tkstack",
  "dotfiles.targetPath": "~/.local/share/tkstack",
  "dotfiles.installCommand": "install.sh --profile devcontainer"
}
```

Alternatively, clone/mount tkstack in the image and use these lifecycle commands
in the consuming project's devcontainer configuration:

```json
{
  "postCreateCommand": "bash /home/vscode/.local/share/tkstack/install.sh --profile devcontainer --workspace /workspaces/project",
  "postStartCommand": "bash /home/vscode/.local/share/tkstack/install.sh --profile devcontainer --workspace /workspaces/project --offline"
}
```

Replace paths with the container's actual checkout/workspace. Arrays are used
in this repository's own hook definition to preserve paths containing spaces.
The first hook can download packages; repeated startup uses cached software.
The bootstrap does not install or authenticate the host applications themselves.

## Codex cloud environments

Install the dotfiles checkout in the environment setup phase while dependency
network access is available:

```sh
# Environment setup script; use a persistent path included in the environment cache.
TKSTACK_DIR="$HOME/.local/share/tkstack"
if [ ! -d "$TKSTACK_DIR/.git" ]; then
  git clone https://github.com/Tyler-R-Kendrick/tkstack.git "$TKSTACK_DIR"
fi
bash "$TKSTACK_DIR/scripts/codex-cloud-setup.sh" --workspace "$PWD"
```

For cached environment startup/maintenance:

```sh
bash "$HOME/.local/share/tkstack/scripts/codex-cloud-startup.sh" --workspace "$PWD"
```

The setup wrapper selects full `codex-cloud` provisioning; the startup wrapper
selects the same profile with `--offline`. Both forward ordinary bootstrap
options. Keep the checkout and its `.tkstack/runtime/` in the environment cache;
if the platform restores only source files, run full setup again. A project-only
setup can use `--target "$PWD" --scope project` instead of changing the home.

No platform API call or environment draft is changed by this repository. These
scripts are inputs for the platform's setup/startup fields. Preserve the supplied
proxy, CA, authentication, and guard variables. Python's standard HTTPS client,
pip, npm, and uv use their normal configured trust/network paths. No interactive
login, model call, extraction/indexing job, proxy routing change, or PR action
is part of bootstrap.

## Toolchains, commands, and state

Python **3.11+**, Bash, and Git are base prerequisites (Python 3.12 preferred).
When needed, bootstrap installs **uv 0.12.23** from a hash-locked Python wheel and
**Node 24.19.0** from an official SHA-256-verified archive, privately under
`.tkstack/runtime/toolchains/`. Existing Node 24+ can be reused. Node archive
extraction needs Python 3.11.8+ or 3.12+ for the safe tar filter; an older 3.11
host can provide Node beforehand. No sudo/system-package change is required.
Linux x86-64/ARM64 and macOS x86-64/ARM64 Node assets are pinned. Host applications,
Git itself, Docker, accounts, and optional GUI daemons are not installed.

Private command shims go in `.tkstack/bin/`; they route to the managed launchers
and include `rtk`, `hf`, `impeccable`, `headroom`, `wikiskill`, `open-design`, `codify`, `skillify`,
`openwiki`, `graphify`, and `graphify-mcp`. They do not shadow the system `od`.
The generated `.tkstack/bootstrap/env.sh` adds that directory idempotently.
Home installs add a small owned source block to `.bashrc` and the existing Bash
login file (or `.profile`). Foreign content is preserved; another checkout's
block or symlink-managed startup file requires using `--no-shell` and adding
that source pointer through its owning dotfiles manager. Project installs do
not create shell startup files in the repository.

Host-launched hooks/tools independently resolve private prerequisites, so MCP
and native hooks work even before an interactive shell sources the file. For a
current shell or a platform that ignores login files, run:

```sh
. /path/to/tkstack/.tkstack/bootstrap/env.sh
```

All runtime versions/download digests come from `harnesses/integrations.json`.
OpenWiki uses its npm integrity lock; Graphify and Headroom use hashed Python
requirement locks. Vendored WikiSkill, Ponytail, and Caveman use pinned sources.
Authored skills/instructions remain in source; user/workspace learning stores
initialize through their actual renderers without copying private source history.
Private run logs live in `sessions/bootstrap-<id>/`; the last result for a target
is `bootstrap/installations/<target-hash>.json`. These are beneath `.tkstack/`
and ignored. An OS advisory lock serializes shared checkout setup and releases
on process death; independent runtime workers run concurrently inside it.

## Completion and manual requirements

A successful bootstrap means the selected software/files are applied and their
local checks passed. Its JSON report keeps `ready`, `configured-with-requirements`,
`failed`, `verified`, and `planned` distinct. Download/install/check failures
return nonzero even if other integrations were configured successfully. A
read-only check detects missing links, native configuration drift, shell pointer
changes, and missing/stale private shims. Default startup reuses matching installs.
Differing or interrupted third-party runtime environments are preserved and
reported for repair rather than silently deleted or upgraded.

OpenDesign needs the official executable selected by `OPEN_DESIGN_CLI` and its
local application/daemon; Stitch registration needs `STITCH_API_KEY`. These
known unresolved prerequisites appear in the report and make `--strict` fail.
Fal OAuth is handled by the harness and is reported as unverified information,
not a claim that setup signed in. Headroom CCR operations need its separately
started proxy; merely installing it does not redirect providers or start one.
No credential value is included in the report. Re-run setup after supplying
required environment variables or external software.

The bootstrap reuses `scripts/install.py`, `setup_integrations.py`,
`setup_lever.py`, `doctor.py`, shared state initialization, and the native runtime
installers. Those narrower commands remain available for focused maintenance.

The shared Markdown command runtime (`command-schema`) is another automatic
Python recipe: PyYAML 6.0.3, jsonschema 4.26.0, and hashed transitive dependencies
from `skills/codify/requirements/requirements.lock`. The `codify` and `skillify`
shims launch their actual source tools through that private interpreter, so
fresh hosts need no system-level YAML/JSON Schema packages.

## Scoped skill/workflow executable

Setup also generates `<state-root>/tkstack` in its source, workspace, and user
initialization roots, plus the `tkstack` PATH shim. These launch the deterministic
Codify-based runner with the private command interpreter. Full setup and cached
startup apply/check owned entrypoints; foreign or modified programs are preserved.
Use `scripts/runner_install.py --scope global` only for an explicitly selected
machine scope. [Runner documentation](runner.md) covers exact CLI examples,
scoped registries, and the existing Vercel AI SDK model/provider profile format.

## Repository documentation hooks

`harnesses/bootstrap/profiles.json` is the shared source for profile selection
and the README's generated profile table; `bootstrap_profiles.py` validates its
version, unique supported harnesses, and Copilot boolean. Toolchain pins in the
same directory drive the generated prerequisite versions.

Full setup also installs this source Git checkout's pre-commit documentation
gate, preserving/chaining any prior pre-commit handler. Project installation
into the source checkout registers repository-only Codex/Claude/Cursor completion
hooks; home/other project installations do not add this repo's completion gate.
See [documentation maintenance](documentation.md) for review snapshots, staged
checks, native hook trust/reload, and restoration of the previous Git hook.

## Owned skill conformance

Doctor runs `scripts/check_skills.py` through the managed hash-locked command
interpreter when that runtime is ready; an offline first setup reports this check
as pending alongside its missing-runtime requirements. It checks all 19 owned schemas, command surfaces, native bindings,
shared runtime/state copies, marketplace metadata, current executable artifacts,
and reviewed train/validation/test decision suites. This performs no model or
provider job. The repository CI checks the same contract and behavior fixtures;
see [normalization and evidence](normalization.md).
