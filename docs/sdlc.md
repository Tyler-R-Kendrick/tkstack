# SDLC workflow

Invoke `/sdlc` in Claude Code or Cursor, or `$sdlc` in Codex, followed by the
development workload. Restart the harness after installation to discover the
skill. [The skill](../skills/sdlc/SKILL.md) is user-invoked and portable across
harnesses; it uses the active harness's real agent and PR tools.

For a scoped request, use `/sdlc plan`, `/sdlc design`, `/sdlc verify`,
`/sdlc review`, `/sdlc deliver`, or `/sdlc handoff` with the actual target. These
select the matching reference and keep that boundary; review alone does not
start worktrees, agents, publication, or merging. A full implementation request
loads the complete operating guide and retains all lifecycle requirements below.

The outer loop defines the outcome, decomposes it, challenges the result, and
delivers it. Each worker runs an inner red → green → refactor loop at a public
behavior or contract seam. Given/When/Then scenarios and real consumer/provider
contract verification provide acceptance coverage. Browser captures document
relevant behavior without making an E2E suite the acceptance dependency.

Unexpected development findings can return the inner loop to outer-loop
requirements and architecture work. Record the issue, pause affected descendants,
stop their writers, and append authorized workload/scenario revisions and ADR
decisions. Replan and invalidate affected evidence before resuming red/green;
independent unaffected branches can continue. Preserve the original workload and
reconcile every changed, added, or withdrawn requirement in final review.

## Durable task state

New runs use embedded SQLite WAL in the selected workspace/user/global
`.tkstack/sdlc/task-graph.sqlite3`, with no separate server. The database,
WAL/SHM, and retained private evidence are gitignored and survive session cleanup.
Init snapshots the graph and original workload; status/history resume across
harness restarts. Use local storage with SQLite locking, not network replication.

```sh
.tkstack/tkstack skills sdlc -- help
.tkstack/tkstack skills sdlc -- help tasks claim --format man
.tkstack/tkstack skills sdlc -- version
.tkstack/tkstack skills sdlc -- tasks init --run example --actor lead --graph task-graph.json
.tkstack/tkstack skills sdlc -- tasks claim --run example --actor worker-a
.tkstack/tkstack skills sdlc -- tasks status --run example --actor lead
```

Claims pin exact input heads/proofs and return expiring owner tokens. Heartbeat
before expiry; finish with the token and actual proof. Expiry never silently
reassigns a worktree: coordinator recovery requires observed quiescence evidence.
Use `issue`, `quiesce`, and `revise` for the return to the outer loop; architecture
issue resolution requires a retained ADR. Revisions preserve originals, track
requirement dispositions, and invalidate affected downstream results. `gate`
checks task readiness; independent original-workload evidence and live PR gates
remain required. [Coordination details, commands, templates, and recovery](../skills/sdlc/references/durable-task-graph.md)
describe the exact contract and the compatible legacy JSON scheduler.

The compiled artifact executes coordination without inference. SQLite publishes
changes in short version-checked transactions outside Git/proof I/O, updates
changed task rows, and batches branch-ref reads. Static ownership/cycle checks
run at graph registration/revision. The complete engineering lifecycle still
requires actual agents, evidence judgments, and authorized delivery operations.

## Workload to delivery

1. Freeze the complete initial workload and each branch's assigned workload.
   Give requirements stable IDs, scenarios, compatibility expectations, and
   evidence applicability. Preserve later authorized amendments separately.
2. Build the smallest independently verifiable deliverables into a DAG. Pin
   inputs, give each branch exclusive write ownership, and claim ready work
   atomically within the real CPU, memory, disk, and agent budget.
3. Give every implementation, review, and mitigation branch its own sparse
   worktree. Verify actual COW before dispatch; share concurrent-safe caches
   while keeping mutable installations, build outputs, and capture state private.
4. Parallelize independent implementations and adversarial review. Retain
   red/green results and relevant sanitized HARs, matched before/after
   screenshots, recordings, or other diagnostics with commands, revisions,
   fixture metadata, and hashes. Commit coherent green increments.
5. Integrate and independently recheck mitigations. A final reviewer compares
   every initial requirement and amendment to the actual current evidence.
   Bind approval to the exact workload, Git head, and evidence payload.
6. Publish small stacked PRs, address all comments and threads, and keep CI
   green. Land accepted code dependencies first using squash merges, restack
   children from saved parent boundaries, and refresh their proof and review.

Installation does not start agents, publish PRs, or merge this repository.
An implementation invocation follows the task's established publication and
merge scope without adding redundant permission checkpoints.

## Templates and helper

Start with the skill's [workload](../skills/sdlc/templates/workload.md),
[task graph](../skills/sdlc/templates/task-graph.json),
[evidence plan](../skills/sdlc/templates/evidence-plan.json),
[task result](../skills/sdlc/templates/task-result.json),
[evidence manifest](../skills/sdlc/templates/evidence.json), and
[independent review](../skills/sdlc/templates/review.md). Placeholders and pending
verdicts require actual inputs; templates do not assert success.

The Python standard-library helper needs Git and a filesystem clone utility
for COW. From this repository:

```sh
python3 skills/sdlc/scripts/sdlc.py --help
python3 skills/sdlc/scripts/sdlc.py freeze --help
python3 skills/sdlc/scripts/sdlc.py graph path/to/task-graph.json
python3 skills/sdlc/scripts/sdlc.py worktree --help
python3 skills/sdlc/scripts/sdlc.py claim --help
python3 skills/sdlc/scripts/sdlc.py finish --help
python3 skills/sdlc/scripts/sdlc.py review-digest path/to/evidence.json
python3 skills/sdlc/scripts/sdlc.py gate --help
```

Graph workload paths resolve relative to the graph file. Keep baseline, leases,
reports, and evidence in an owned retained location; keep task worktrees and
shared-cache roots outside existing checkouts. The references explain
[worktree provisioning](../skills/sdlc/references/worktrees-and-swarm.md),
[evidence formats](../skills/sdlc/references/evidence-format.md), and
[review/restacking](../skills/sdlc/references/review-and-stacks.md).

## Verified limits

The current workspace filesystem rejects guaranteed reflink copies. Strict
`--require-cow` mode fails before branch creation; use a reflink-capable volume
to meet that requirement. An explicitly permitted fallback uses sparse files
and shared Git objects and reports that mode accurately. Shared Git objects
alone do not establish filesystem COW.

The offline gate checks structure, identity, hashes, and coverage. A real
independent reviewer must judge whether the evidence proves the requirements.
The merge gate also needs freshly observed native-host CI, approvals, comments,
dependencies, and mergeability; local JSON cannot authenticate remote state.

Automated behavior checks exercise real temporary Git repositories, sparse
worktree isolation, task ownership and stale proof rejection, contract identity,
per-requirement artifacts, and exact-payload review invalidation. Synthetic
reports test the helper's rules; they do not claim production provider checks,
browser captures, remote CI, or an actual merged PR stack.
