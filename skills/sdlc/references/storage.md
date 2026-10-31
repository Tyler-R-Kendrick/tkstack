# Scoped tkstack storage

For durable SDLC coordination use scoped `.tkstack/sdlc/task-graph.sqlite3`,
not `sessions/<session>/sdlc/`, even when a session ID is set. Preserve it and
retained proof across temporary cleanup. See [durable task coordination](durable-task-graph.md).

Custom skills use `.tkstack/` at three levels, independently of the harness.

| Scope | Default root | Override |
| --- | --- | --- |
| Global / machine | `/etc/.tkstack` | `TKSTACK_GLOBAL_DIR` |
| User / personal | `~/.tkstack` | `TKSTACK_USER_DIR` |
| Workspace / repository | `<workspace>/.tkstack` | `TKSTACK_WORKSPACE_DIR` or explicit `--project` |

Overrides select an actual directory named `.tkstack`. Explicit `--project`
selects that exact workspace and wins over its environment override. Defaults
are POSIX conventions; another host can configure the roots explicitly. Location
discovery never creates directories. Writes select one scope (workspace by
default); a missing directory or permission failure never redirects a write to
another scope. Global setup uses the host's normal permissions; supporting it
does not require creating a system directory during repository installation.

Curated knowledge can be read in workspace > user > global order. The nearest
rule with the same ID shadows a broader rule, including when retired/candidate;
only active effective rules are applied. Rule trigger/domain scope still matters:
a storage level does not turn a workspace convention into a universal preference.
An installed `.agents/steering` alias remains a supported explicit shared store;
it is a pointer, never another state tree. Existing `--store`/TKSTACK_STEERING_DIR
selection remains available. `learn --scope` selects its requested level directly.

Each root has its own `.gitignore`. Sessions, raw histories, reviews, evidence,
caches, leases, and locks are private and ignored. The policy and compact
`reuse/catalog.json` may be versioned. New generated namespaces are ignored by
default. Authored code, skills, workflows, lint/hook definitions, instructions,
and published documentation keep their requested/native source locations;
choose their destination scope explicitly during promotion.

| Content | Location beneath the selected root |
| --- | --- |
| Temporary notes, working copies, observations, transcripts, handoffs | `sessions/<session>/` (optionally `<skill>/...` below that) |
| Session-specific evidence, workload, plans, measurements | `sessions/<session>/evidence/`, `sdlc/`, `hill-climb/`, etc. |
| Durable correction ledger, scoped rules, anti-slop criteria/views | `steering/` |
| Saved session reviews, abstract findings, promotion records | `learnings/reviews/<content-hash>/` |
| Shared dependency caches, installed runtimes, native adapter state | `cache/`, `runtime/`, `state/` |
| Cooperative writers and cross-session leases | `locks/` |
| Durable reusable-asset discovery metadata | `reuse/catalog.json` |
| Legacy run/evidence trees | Retained in place; new active sessions use `sessions/<session>/` |

## Paths and temporary sessions

All custom packages bundle the same `scripts/tkstack_state.py` primitive:

```sh
python3 <skill-directory>/scripts/tkstack_state.py locations --project /repo
python3 <skill-directory>/scripts/tkstack_state.py path --scope user --namespace steering
python3 <skill-directory>/scripts/tkstack_state.py init --project /repo --session session-123 --namespace sessions
python3 <skill-directory>/scripts/tkstack_state.py path --project /repo --session session-123 --namespace evidence
```

`path`/`locations` are read-only. `init` creates the selected path and its protected
ignore policy. The helper resolves the active workspace, not its installed
package directory. Session IDs are literal 1–128 character names, starting with
a letter/digit and containing only letters, digits, dot, underscore, or dash.
Traversal, separators, metacharacters, and session symlinks are rejected.

Set `TKSTACK_SESSION_ID` once for the harness/task session. `state_path()` then
puts session-local runs, evidence, scratch, SDLC/optimization records, and
conversion plans under `sessions/<session>/<namespace>`. Shared caches, locks,
steering, runtimes, and reuse metadata stay outside that temporary directory.
Explicit `session_path(id, project, scope)` and
`state_path(namespace, project, scope, session=id)` support direct callers.
Without a session ID, legacy namespace paths remain usable; new workflows should
establish a named session rather than invent competing run directories.

`session_tempdir()` owns and removes only its unique scratch child. A named
session remains for Learn to inspect; an anonymous temporary session is removed
when empty. Concurrent calls have separate mutable directories. Codify uses
this primitive for its materialized execution image. Required atomic-publication
temporaries remain beside their target and are cleaned up normally.

## Review, generalize, then expire

A session is temporary evidence, not an executable instruction source or a
permanent home for a reusable procedure. Learn can list/start/close sessions,
collect bounded evidence, and route abstract findings to durable mechanisms.
See its packaged session-consolidation reference. Saved reviews and extracted
corrections/experiences are outside `sessions/`, so useful learning can survive
session cleanup. Durable artifacts belong to their canonical source owner.

Closing a session marks it available for review; it does not delete it. This
implementation has no automatic TTL/deletion job. Before explicitly removing
session data, preserve needed evidence, apply and verify useful generalizations,
and retain pending findings or explain why they stay local. Do not remove
another writer's active session. A crash may leave ignored scratch behind.

Private writers use `ensure_state()`, which rejects escape paths, preserves
foreign ignore rules, maintains a marked private-policy block, and uses bounded
cooperative locking plus atomic publication. Reports, audits, list/path helpers,
and unsaved review/plan commands do not initialize state.

## Compatibility

Existing root-level `steering/` and `reuse/` were previously moved losslessly into
`.tkstack/`. Existing run/evidence data remains intact; no historical files are
silently moved or deleted by scoped discovery. Standalone skills default to the
active workspace; user/global writes require an explicit selection. Installer
startup pointers load layered curated rules; they do not mine private harness
transcript databases. Fresh clones initialize an empty local learning store.
Vendor snapshots, host credentials, existing home configuration, and native
source deliverables are preserved.
