# Executable artifact contract

`tkstack.codify/v1` is a canonical JSON build artifact, not a prompt cache or
another orchestration language. It freezes:

- Compiler name/version and a SHA-256 of canonical artifact content.
- Source and contract-case paths/hashes relative to the build root.
- Root locator relative to the lock location, so relocating the complete tree works.
- A native Python/Node entrypoint and sorted code/resource inventory, each with
  SHA-256, file mode, and base64-encoded exact bytes.
- Declared inference mode/profile names and passed case IDs/repetition count.
- Caller-supplied `--include` paths, sorted and unique, relative to the build
  root (`.` is the root). Locks compiled before this field omit `includes`.

The lock contains the **actual runnable code bytes**. `run` validates the lock,
checks current source/code/cases, writes that frozen image into an isolated
`.tkstack/sessions/<session>/codify-*/work/`, and invokes the native interpreter. It does
not execute the mutable source implementation or ask a model to reconstruct it.
The scratch copy is removed on ordinary completion/failure. Named sessions and
the ignore policy remain for consolidation; empty anonymous sessions are removed.
Crash leftovers stay ignored. Locks serialize only publication to the same
artifact path; independent build preparation, verification, and runs can overlap.

Publication checks source/case/code drift and prior output contents. Ordinary
failures leave the previous artifact intact. Cooperative writers use
`.tkstack/locks/codify/`; publication is an atomic same-directory replacement.
A crashed lock can require inspection/removal. Nonparticipating concurrent
writers are not covered by a filesystem-wide transaction. Generated artifacts
are authored deliverables and can be checked in; private compile/run state is
ignored by `.tkstack/.gitignore`.

`check` and `run` fail on a stale source, case file, or included implementation.
`check` also rebuilds the snapshot from the entrypoint directory, `commands/`
when that directory exists, the package root when `scripts/contract.json`
exists, and each path in `includes` when the lock records that field. A file
in that inventory that the lock does not name is stale, so adding a reference
after compilation fails until an explicit recompile. A lock that omits
`includes` was compiled before those paths were recorded: `check` rebuilds
the entrypoint directory, `commands/`, and the contract package root, and
still compares every file the lock names. A nested directory with its own
`SKILL.md` is a separate package and stays on its own lock. `check` drops
that package before applying the snapshot limits, so subskill growth does
not exhaust the parent inventory. Snapshots retain Git-portable executable
modes (0644/0755). Freshness compares
the executable bit, so checkout umasks that change owner/group read/write bits
do not invalidate identical code. Changing executable status still invalidates
the artifact. Existing locks retain compatibility. This is source execution-mode
tracking, not an ACL or host filesystem-permission preservation mechanism.
Recompile explicitly. The runner never falls back to Markdown or silently
regenerates the artifact. Complete source trees are required for freshness;
there is currently no detached-source or ignore-staleness execution mode.

Inventory discovery excludes `.git`, `.tkstack`, `node_modules`, and
`__pycache__`, and the selected output itself. A package with
`scripts/contract.json` snapshots the whole package, so keep generated files
out of that tree. Other workflows snapshot the entrypoint directory and
`commands/`; include imported code outside those directories explicitly.
Compile records those `--include` paths. Inventory limits apply to the files
that remain after nested skill packages are omitted: 512 files and 16 MiB of
base64 data. Lock parsing also caps total file size at 16 MiB. This is not an
import tracer or a hermetic build system.

Python uses the selected interpreter/standard library; Node needs its actual
compatible runtime. AI SDK packages are pinned by the frozen npm lock and
installed separately; an explicit dependency directory is linked into each
private run. Direct package versions are checked, but that does not attest every
transitive installed byte. Use a clean `npm ci` result and native checks.

Digest/provenance checks detect drift and corruption; they are not signatures or
an authority grant. Case evidence is checked against the recorded IDs/source,
but a malicious party can author a new lock and digest. Review code and use
normal repository trust controls. Compiling/running executes trusted code with
normal process authority, not a sandbox. Input/output/deadline bounds do not
constrain every descendant's resource or network behavior. `mode: none` records
the reviewed inference contract; a SHA or passing cases cannot prove arbitrary
code never calls a model. Measure actual executions where that matters.

## Bounded nested execution

An outer invocation owns a process group and terminates remaining group processes
on completion, failure or deadline. Native helper and nested Codify executions
share that ownership rather than detaching their case workers into new groups.
A directly invoked native adapter owns its own helper group. Explicitly detached
daemons are outside this group contract; this remains trusted code execution,
not an operating-system sandbox or general service manager.
