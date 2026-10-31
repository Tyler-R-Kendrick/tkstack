# Sparse worktrees and the subagent swarm

Read this before dispatching a graph frontier. The coordinator owns scheduling,
branch leases, integration heads, and shared-cache maintenance. Each worker owns
one accepted deliverable and one writable task branch at a time.

## Build useful atoms

Split until each node has one observable outcome, one acceptance seam, a bounded
write set, and a small independently reviewable change. A contract definition,
one provider behavior, and one consumer behavior can be separate atoms. A few
lines that cannot be accepted on their own are still part of the same atom.

For every node, record requirement IDs, its deliverable, acceptance conditions,
evidence obligations, owned paths, sparse paths, dependencies, branch, and base.
Use a dependency only when the node needs another node's output or must follow
its write ownership. Shared read access alone does not create an edge. Settle
shared contract shapes first, then let providers and consumers proceed in
parallel against that version. Give a shared implementation file one writer,
or split its interface before increasing concurrency.

The task DAG and the PR stack are different structures. A node may need several
inputs, but a PR has one base. `pr_parent` identifies the code ancestry; the
other dependency heads remain explicit verification and readiness inputs.
Independent siblings can form separate stacks over the same contract PR.

## Provision an isolated branch

Resolve and record the exact base SHA before dispatch, including the saved head
of a declared PR parent. A moving branch name is a lookup input, not the proof
of what was checked out. Allocate a unique worktree outside other worktrees and
the source checkout. Preserve existing work; never repurpose an occupied branch
or directory.

Each branch needs its own Git index and writable checkout. Use Git worktrees
sharing the repository's object database. Configure sparse checkout through
Git's worktree-aware sparse-checkout support; verify that each worktree's
patterns stay local rather than changing the main checkout or a sibling.
After a `--no-checkout` worktree has its cone set, materialize the index and
selected files with `git -C <worktree> read-tree -mu HEAD`. Setting sparse
patterns alone can leave the checkout empty; the helper verifies materialized
files and clean status rather than treating configured patterns as success.
Provision review and mitigation graph branches the same way. Read-only Git
object inspection can supplement their own worktrees without sharing a worker's
mutable checkout.

Worktrees isolate Git indexes and checked-out files; they are not an operating
system security boundary. Set each agent's working directory and use available
harness path restrictions. Before accepting completion, compare the task's
diff against its declared ownership. The helper checks committed paths and
pinned dependency heads; the coordinator also inspects uncommitted changes and
private runtime artifacts.

Sparse paths must cover the owned source, its real contracts and verification
fixtures, relevant shared interfaces, and build tooling. Include the root
instructions, dependency/lock manifests, and test configuration the selected
checks consume. Cone-mode paths are directories, not ownership globs: use a
separate `sparse_paths` list when necessary. Widen the cone deliberately when a
real dependency is missing; a missing file is not a reason to skip a check.

Use the bundled helper with the complete sparse dependency closure:

```sh
python3 <skill-directory>/scripts/sdlc.py worktree \
  --repo <repository> \
  --root <workspace>/.tkstack/worktrees \
  --branch sdlc/<workload>/<task> \
  --base <resolved-base-sha> \
  --path contracts/example \
  --path src/provider \
  --path tests/contracts/provider \
  --seed <pristine-commit-matched-seed> \
  --cache-root <workspace>/.tkstack/cache \
  --require-cow
```

Record the returned path, base SHA, storage mode, COW capability, shared-object
status, and cache locations in the task lease. Check that the initial checkout
is clean before the worker edits it.

## Copy on write is a filesystem capability

Git worktrees share Git objects. That alone does **not** make checked-out files
copy on write. This workflow requests a real reflink-backed checkout for each
task branch. Use an immutable seed addressed by its exact commit and sparse
path set. Verify that its selected tracked contents and modes match that base,
and keep agents from editing the seed. Never seed from a worker's dirty tree,
ignored build products, or an unverified dependency checkout.

Probe the actual seed/destination filesystem pair. A guaranteed reflink
operation, such as Linux `cp --reflink=always` or a successful native clone-file
API, establishes COW support. A best-effort copy option does not. Seed and task
checkout must be on a filesystem combination that supports the operation.

Clone selected regular files into distinct destination inodes with independent
metadata. A worker's write must leave the seed and sibling unchanged. Preserve
Git-managed symlinks as symlinks rather than following them into other trees;
keep Git metadata, indexes, and runtime output separate. Never hardlink mutable
source, installed dependencies, or build output to simulate COW.

`--require-cow` leaves provisioning unready when reflinks are unavailable. If a
documented sparse/shared-object fallback is permitted by the task, record its
actual storage mode and disk cost; never report it as COW. Keep strict COW
requirements blocked until a suitable volume or an explicit scope change is
available. An unsupported filesystem does not stop independent graph work.

## Share cache, isolate mutable state

Share only package-manager or compiler caches that support concurrent access
and validate their content. Examples include verified package download stores,
wheel caches, and content-addressed compiler caches. Let the cache's own locking
and atomic publication protocol arbitrate concurrent writes. Keep cache keys
sensitive to the toolchain, platform, dependency lock, and relevant build flags.
The helper returns a conservative cache environment; inspect it before use.

Keep each branch's dependency environment, `node_modules`, virtual environment,
`target`/`dist` directories, test databases, browser profiles, logs, and running
servers private. Content-addressed package bytes may be reused through verified
COW/copy installation; writable dependency trees are not a shared cache. Assign
unique ports and database namespaces. Bound disk growth and cache eviction at
the coordinator, outside active cache writes.

## Dispatch the ready frontier

Use the [SQLite coordinator](durable-task-graph.md) for new runs. Keep its
database outside sessions, hand each owner its lease token and workload hash,
and renew before expiry. After a restart inspect owners/issues instead of
recreating the graph. Expired state cannot establish that a worktree writer has
stopped. Quiesce/recover explicitly before reassignment. Unexpected scope/design
findings pause their downstream closure and re-enter outer-loop planning;
authorized revisions invalidate affected results and retain the original plan.

1. Select nodes whose declared inputs are accepted and whose write leases are
   free. Claim each node atomically with an owner and recorded base/input heads.
2. Fit fan-out to real CPU, memory, disk, process, and harness-agent limits.
   Reserve capacity for review and mitigation instead of starting every server
   at once. Broaden concurrency when resources and independent atoms allow it.
3. Start each worker with a fresh focused context: the frozen workload pointer,
   task ID, exact base/input SHAs, owned paths, acceptance and evidence plan,
   cache environment, and reporting destination. Keep unrelated transcripts out.
4. Run independent adversarial reviewers against immutable worker heads in
   their own detached/sparse review worktrees. They test the
   requirements and assumptions rather than trusting a worker's completion claim.
5. Route findings to the owning atom. A mitigation worker receives the finding,
   requirement, reproduction/evidence, and an exclusive writable lease. Handoff
   the existing branch lease or create a declared child; never let two agents
   edit the same branch or worktree concurrently.
6. Release the lease with exact commit heads, evidence references, check results,
   and remaining findings. Dispatch the next frontier while unrelated branches
   continue. A green unrelated branch cannot satisfy a dependency edge.

An integration reviewer needing several sibling outputs gets a disposable,
recorded integration head containing those exact heads. Keep this join separate
from PR ancestry; it does not turn a DAG into a fictitious multi-base PR. Repeat
integration verification when any input head changes. Split mitigations across
owning branches when findings span multiple atoms.

Done when every dispatched node has an accountable owner, isolated storage,
verifiable inputs, and a retained result. Concurrency is measured by useful
independent work completed; skipped tests and undocumented storage fallbacks
do not count as throughput.
