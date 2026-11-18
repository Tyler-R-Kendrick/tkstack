# Executable artifact contract

`tkstack.codify/v3` is the only format emitted by current builds. The runner
also reads existing v1 and v2 locks. These canonical JSON artifacts freeze:

- Compiler name/version and a SHA-256 of canonical artifact content.
- Source and contract-case paths/hashes relative to the build root.
- Root locator relative to the lock location, so relocating the complete tree works.
- A native Python/Node entrypoint and sorted code/resource inventory, each with
  SHA-256, file mode, and base64-encoded bytes. V2 and v3 optionally compress each
  file with zlib before base64; decompression is bounded and hashes cover the
  original bytes. A v1-only runner cannot read v2 or v3 locks; a v2-only
  runner cannot read v3 locks.
- A no-inference declaration and passed case IDs/repetition count.
- Caller-supplied `--include` paths, sorted and unique, relative to the build
  root. New builds accept individual files only; older locks may contain
  directories or omit this field.

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

`check` and `run` fail on stale source, cases, command definitions, manifest,
or declared runtime files, including changed executable modes. For existing v1
and v2 locks, the runner still checks their recorded legacy inventories. New
builds never create a whole-package or directory snapshot.

Every new build requires `scripts/lock-runtime.json` containing
`{"version": 1, "files": ["relative/path", ...]}` with sorted unique file
paths. An empty list is valid when the entrypoint needs no other files. The
compiler embeds those regular files, the manifest, the entrypoint, command
definitions, and any explicitly included individual files; it separately hashes
source and cases. The scaffold supplies a starter manifest. Review and update it
when the implementation changes, including after normalization. The compiler
rejects missing manifests, directories, symlinks, undeclared native
entrypoints, and recognizable same-directory Python imports missing from the
inventory. Dynamic imports, conditional resources and external runtime data
still require human review and real behavior tests; static checks do not prove
completeness. Missing dependencies discovered by the compile cases fail the
build, which leaves the prior lock intact.

Files outside the declared inventory do not stale a new lock. A complete source
tree is still required to check freshness; there is no detached-source or
ignore-staleness mode. Inventory limits remain 512 files and 16 MiB of base64
data before compression. Decoding retains the same aggregate bound and rejects
trailing, truncated, malformed and oversized compressed streams. Lock parsing
also caps the serialized file at 16 MiB. This is not an import tracer, a
hermetic build system, or a guarantee that arbitrary large programs fit a
particular hosting limit.

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
the reviewed host boundary; a SHA or passing cases cannot prove arbitrary
code never calls a model. Measure actual executions where that matters.

## Bounded nested execution

An outer invocation owns a process group and terminates remaining group processes
on completion, failure or deadline. Native helper and nested Codify executions
share that ownership rather than detaching their case workers into new groups.
A directly invoked native adapter owns its own helper group. Explicitly detached
daemons are outside this group contract; this remains trusted code execution,
not an operating-system sandbox or general service manager.
