# Durable task coordination

Read this when scheduling work, restarting coordination, recovering an owner,
or taking an unexpected development finding back to requirements or design.

The deterministic coordinator uses Python's embedded SQLite in WAL mode. It
needs no server, port, daemon, model, or new dependency. The default database is
`<selected-root>/.tkstack/sdlc/task-graph.sqlite3`. Select workspace, user, or
global with `--scope`; `--database` can select another file under `.tkstack/sdlc/`.
An explicit database path overrides scope. Scope never falls back on permission
errors. Keep the database on a local filesystem with working SQLite locks;
network shares and independently replicated copies are unsupported. Workers on
other machines must use a coordinator on the owning machine rather than copy
the database. A server backend is warranted only when that topology is required.

This state is durable across process and harness restarts. It deliberately
bypasses the shared helper's session-local `sdlc` namespace: even with
`TKSTACK_SESSION_ID`, the graph remains outside `sessions/<session>/`. Scratch
captures can stay in sessions, but promote required evidence to durable retained
paths before closing a task. Initialization installs the shared `.tkstack`
ignore policy, which ignores the entire `sdlc/` directory, including SQLite,
WAL, SHM, workload snapshots, and receipts. Nothing here belongs in Git.

## Invoke and register

From a provisioned workspace:

```sh
.tkstack/tkstack skills sdlc -- help
.tkstack/tkstack skills sdlc -- tasks init \
  --run checkout --actor lead --repo /repo --graph /repo/task-graph.json
.tkstack/tkstack skills sdlc -- tasks status --run checkout --actor lead
.tkstack/tkstack skills sdlc -- tasks claim --run checkout --actor worker-a --ttl 900
```

Use the graph/workload templates and existing `sdlc.py freeze` first. Init
validates the complete graph once: cycles, declared requirement coverage,
branch uniqueness, concurrent path ownership, and actual workload bytes. It
retains the immutable initial graph and UTF-8 workload in SQLite. A run ID is
unique in a database and bound to the Git common directory, so linked worktrees
share identity but a different repository cannot reuse the run. Editing the
external graph JSON does not update a run; use an explicit revision.

Each command's Markdown frontmatter is its OpenAI Responses function signature
and separate CLI binding. The `operation` parameter has a fixed enum value and
a CLI default. All API parameters are required, with nullable values where
optional; CLI defaults cover omitted optional flags. Export through
`.tkstack/tkstack tools skills sdlc --format responses` or `--format chat`.
Both CLI and tool calls dispatch the same verified artifact; no inference runs.
Aliases omit the `tasks` prefix. Missing command and reserved `help` generate a
man page with deterministic console rendering. Use `help tasks claim --format
man` for man(1) source and reserved `version` for declared package metadata.
Skillify supplies these builtins; they run without the task artifact or state.

For a standalone copy without tkstack's dispatcher, use the same implementation:

```sh
python3 <skill-directory>/scripts/task_graph_tool.py --input request.json
```

The request is a JSON object with `operation`, `run`, `actor`, and the parameters
defined in the matching command page. Relative external paths are resolved
against the selected workspace, including when Codify materializes code in
private scratch. `TKSTACK_WORKSPACE_DIR` explicitly selects that root for a
standalone or shared Codify invocation. The native helper needs only Python and
Git; typed CLI parsing needs the installed shared command runtime. Existing
`sdlc.py` worktree, freeze, review-digest, and evidence gate commands still apply.

## Lease and proof protocol

Claim deterministically chooses the first ready node in graph order, or the
requested `--task`. It pins base/input commits, input proof digests, the graph
revision, and the claimed workload SHA. It returns an opaque token and expiry.
Only that actor and current token can heartbeat, finish, or quiesce. Store the
token in the worker handoff, not a committed file. The owner label is local
coordination metadata, not authentication; the token fences stale publications.

```sh
.tkstack/tkstack skills sdlc -- tasks heartbeat \
  --run checkout --actor worker-a --task contract --token <token> --ttl 900
.tkstack/tkstack skills sdlc -- tasks finish \
  --run checkout --actor worker-a --task contract --token <token> \
  --outcome done --head <commit> --proof /repo/.tkstack/sdlc/checkout/contract-proof.json
```

Renew before expiry; TTL is 10–86400 seconds, default 900. Done reuses the
existing scheduler's actual Git ownership/head/dependency checks and retained
[task proof](../templates/task-result.json). Its workload hash must be the one
returned at claim. `blocked` retains the record; `retry` releases stopped work
without accepting a result. Both acknowledge that writes have stopped. A blocked
record needs coordinator recovery or a relevant graph revision before reuse.
The full workload/evidence gate still requires BDD, real producer/consumer
contracts, artifact applicability, findings, and independent review.

Expired leases remain reserved and count toward capacity. Status reports them;
it never automatically starts a second writer on their worktree. An owner that
has stopped writes calls `quiesce` while its lease is live. For an expired or
blocked lease, the coordinator verifies termination/ownership release and calls
`recover --task ... --reason ... --evidence '["/retained/worker-exit.txt"]'`.
Live leases cannot be recovered; dependent live workers must quiesce first.
Recovery preserves the old record in history; the next claim gets a different
token. A process that still has filesystem access can still write: tokens fence
state publication, so actual worker termination/quiescence is indispensable.

## Unexpected development issues return to the outer loop

Ordinary defects within the current acceptance and ownership stay in red/green.
Pause and raise an issue when a discovery changes the meaning or feasibility of
requirements, a shared contract, architecture, ownership, or the work graph.
An environment outage is a blocker, not a behavioral red reproduction. Do not
invent a new approval step for an already authorized implementation decision.

1. Capture the observation, reproduction, and retained evidence. Submit
   `tasks issue --run ... --actor ... --issue '<JSON>'` using
   [the issue shape](../templates/issue.json). Stable task/requirement IDs map to
   the affected nodes and every downstream dependent. All explicit issue kinds
   pause that closure; independent branches can continue within available slots.
2. Stop affected worktree writes and acknowledge `tasks quiesce --task ...
   --token ... --reason ...`. Paused workers cannot renew or finish. Inspect the
   issue instead of repeatedly retrying tests against an invalid assumption.
3. The coordinator revisits requirements, acceptance examples, constraints,
   compatibility, and contracts. Resolve routine choices within existing
   authority. When user intent outside that authority is necessary, retain an
   open question and obtain the actual decision; a string saying “approved” is
   not authorization. Code checks the record shape, not the truth of authority.
4. For an architecture resolution, write an ADR describing context, considered
   options, the decision, consequences, and contract/test/migration impacts.
   Supply the retained file and explicit decision in the revision. Every
   architecture issue resolution requires one; code retains its bytes and hash,
   while the coordinator/reviewer checks decision quality and acceptance.
5. Update the workload and graph as an explicit amendment. Use
   [the revision shape](../templates/revision.json) with the expected revision,
   authorization basis, rationale, resolved issue IDs, ADRs, and a reasoned
   `unchanged`, `changed`, or `withdrawn` disposition for **every** prior
   requirement. Withdrawals must be authorized; new requirements must have
   owners and evidence. Never overwrite the frozen initial workload to hide a
   failure. An environment/implementation issue can resolve with unchanged
   requirements and the same workload bytes, recording the actual remedy.
6. `tasks revise --revision '<JSON>'` validates and atomically appends the new
   revision. Changed definitions, changed/withdrawn requirements, resolved issue
   closures, and their old/new downstream dependents invalidate prior results.
   Any affected live worker must quiesce first. Unchanged independent work can
   retain its lease/proof and original claimed workload SHA; the explicit
   unchanged disposition and carry-forward list link that proof to the revision.
   Relocated or removed tasks keep prior results in the revision history.
7. Reassign affected tasks, refresh branch workloads/contracts and exact input
   heads, and re-enter red/green with the revised scenarios. Recollect invalidated
   evidence and independent review; a previously green result is not silently
   accepted for changed behavior. Review unresolved issues again at integration.

The database retains original/revised workload text, graph definitions,
requirement dispositions, ADR text/hash, issue observations/evidence hashes,
invalidated task records, and ordered events. `tasks history` exposes them.
Back up a live database with SQLite's backup API (or close all connections before
copying); copying only the main file while WAL writers are live can lose state.
Do not delete this durable namespace as part of temporary session cleanup.

## Readiness and performance boundaries

`tasks gate` checks the current graph's accepted proofs, actual task branch heads,
dependency heads/proof digests, and absence of open issues. The independent final
review must still compare evidence to the **original workload plus every
authorized amendment/ADR/disposition** using `sdlc.py gate` and the lifecycle
review procedure. It must reconcile added/withdrawn requirements explicitly;
the original-baseline structural gate alone cannot judge amended semantics.
No local database authenticates live CI, comments, approvals, or merge authority.

SQLite uses WAL, FULL synchronous durability, foreign keys, and a five-second
busy timeout. Readers use consistent snapshots; state changes use bounded
compare-and-swap retries and short `BEGIN IMMEDIATE` transactions. Git lookups,
proof hashing, workload validation, and ADR reads happen outside writer locks.
Claims reuse the graph validated at registration, batch branch-ref reads in one
Git call, memoize dependency reuse, and update only changed task rows rather than
rewriting every task record. One run's version is the necessary capacity/graph
publication boundary; independent preparation and reads can overlap. There is
no claim of distributed consensus or a universal throughput gain.

The old JSON `sdlc.py claim/finish --state leases.json` interface remains readable
for existing runs, with its original directory lock and no expiring-token or
revision protocol. New runs use SQLite. To move an active legacy run, stop its
workers, retain its proof, and initialize a new validated run; no silent live
JSON migration or automatic acceptance of previous results occurs.
