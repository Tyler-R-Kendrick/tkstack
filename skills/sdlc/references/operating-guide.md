# SDLC

Own the outer loop from the user's workload to verified delivery. Each worker
owns a tight inner red/green loop at a public behavior or contract seam.

An implementation invocation follows the task's authorized publication and
merge scope through landing. A requested stop at a draft, review, or local
change remains the boundary. Reuse authorization already established in the
session; skill installation or a request to create this skill does not execute
its PR workflow. Preserve existing work and keep actions within the workload.

## 1. Define and freeze the workload

Read the repository's instructions and shared steering rules. Discover the
actual test runners, Git/PR conventions, harness delegation tools, model access,
filesystem capabilities, and available resource budget.

Read [development loops and contracts](../references/loops-and-contracts.md), then
fill [the workload definition](../templates/workload.md). Capture stable requirement
IDs, Given/When/Then scenarios, real producer/consumer boundaries, compatibility,
acceptance, exclusions, and applicable evidence before implementation. BDD and
contract tests are the acceptance strategy; use narrow component tests where
appropriate. Browser evidence does not require adding an E2E suite.

Freeze both the complete initial workload and each task branch's assigned
workload. Branch atoms state their own bounded acceptance obligations and trace
back to the original requirement IDs. A contract-publication atom may prove an
additive contract artifact; it must not claim that an unimplemented producer
already satisfies it. The final integration gate proves the full behavior.

```sh
python3 <skill-directory>/scripts/sdlc.py freeze \
  --repo <repository> --workload <workload.md> --out <repository>/.tkstack/sdlc/<run>/baseline \
  --requirement R-001 --requirement R-002 \
  --evidence-plan <evidence-plan.json>
```

Start the plan from [the evidence-plan template](../templates/evidence-plan.json).
Each requirement declares check kinds and required artifact kinds. The helper
defaults to BDD plus contract verification; a non-behavior atom can select an
appropriate deterministic check with a workload-backed rationale. Visual work
requires matched before/after captures; HAR files, recordings, and traces are
required when they prove a relevant acceptance condition. Keep the hash in the
external baseline manifest, outside the frozen workload's own bytes.

Done when the original outcome, branch scope, test seams, and evidence
obligations are fixed and traceable. Later scope changes are separately
authorized, hashed amendments; retain the original requirements in review.

## 2. Atomize and schedule a useful concurrent graph

Read [worktrees and the swarm](../references/worktrees-and-swarm.md). Fill
[the graph template](../templates/task-graph.json) with the smallest independently
acceptable deliverables: one observable behavior or contract change, one owner,
one write scope, and one proof obligation per atom. Split work as far as it can
remain independently verified and delivered. A line count or a half-finished
layer is not a deliverable.

Use only actual data, contract, and write-ownership dependencies. Publish shared
contract shapes first, then parallelize independent providers and consumers.
Keep DAG dependencies separate from each PR's single parent/base. Pin exact
input heads; join reviewers use a recorded integration head containing the
required siblings rather than a fictitious multi-base PR.

Run `sdlc.py graph <task-graph.json>`. It checks workload identity, dependency
cycles, unique branch ownership, and overlapping concurrent write scopes.
Read [durable task coordination](durable-task-graph.md). Register the validated
graph once, then claim the ready frontier atomically from SQLite:

```sh
.tkstack/tkstack skills sdlc -- tasks init \
  --repo <repository> --graph <task-graph.json> --run <run> --actor <coordinator>
.tkstack/tkstack skills sdlc -- tasks claim \
  --repo <repository> --run <run> --actor <native-agent-id> [--task <task-id>]
```

Use returned immutable base/input heads in each handoff. Bound fan-out to real
CPU, memory, disk, and agent slots, reserving review/mitigation capacity. A
dependency's completion requires retained task/workload/head-bound proof;
changing that proof or moving the accepted dependency head blocks reuse.
Retain the returned token and claimed workload hash; renew before lease expiry.
An expired worker does not release filesystem ownership. Inspect durable state
after restarts and verify quiescence before coordinator recovery/reassignment.

## 3. Provision each branch and dispatch the swarm

Create a unique sparse Git worktree for every implementation, review, and
mitigation graph branch. Use `sdlc.py worktree` as described in the worktree
reference, passing `--require-cow`, a pristine exact-commit seed, explicit sparse
cone directories, and a separate shared-cache root. Resolve sparse dependency
closure so real contract checks can run. The helper materializes the index and
verifies clean status and worktree-local sparse configuration.

Git objects are shared. Actual COW requires a successful guaranteed reflink
probe and separate writable file identities. The helper uses private clone
staging and preserves tracked symlinks. Unsupported strict COW blocks dispatch;
use another suitable volume or a fallback already permitted by the task, and
report its actual storage mode. Never silently label a copy as COW.

Share concurrent-safe content-addressed package/compiler caches. Keep mutable
dependency trees, build outputs, environments, ports, databases, browser
profiles, logs, and evidence capture directories private to the branch.

Dispatch focused subagents with fresh contexts: initial workload and hash, task
ID, base/input heads, exclusive paths, contract version, acceptance, evidence
plan, cache settings, and reporting location. Run independent adversarial
reviewers concurrently at stable checkpoints. Give mitigation workers their
own branches or an explicit exclusive-lease handoff. One writer owns a branch
and its mutable worktree at a time. Use the actual harness swarm API; state a
missing capability or resource constraint instead of inventing concurrency.

## 4. Run the inner loop and retain evidence

For one BDD scenario or contract obligation, observe the intended **red** at its
public seam, implement the smallest **green**, refactor under the checks, and
commit a coherent verified increment. Repeat in vertical slices. Distinguish
harness failures from evidence of missing behavior. Preserve red proof as a
reproduction artifact rather than leaving the published branch broken.

Unexpected requirement, architecture, shared-contract, or graph assumptions can
send this inner loop back to the outer loop. Record an issue, pause its affected
closure, stop writers, and revise requirements/scenarios and ADR decisions within
actual authority. Apply an explicit versioned amendment, invalidate affected
proof, then resume replanned red/green work. Independent unaffected branches can
continue. Preserve the original workload and resolve intent outside existing
authority with the actual user; do not silently weaken a failing requirement.

Verify the real consumer and producer against the same pinned contract artifact
and supported version matrix. A matching stub or schema alone does not prove
the producer's behavior. Keep required contract checks green on each supported
version while future additive contract artifacts are developed in parallel.

Collect the evidence chosen in the initial plan: check reports, sanitized HARs,
matched screenshots, scoped recordings, traces, or command transcripts. Keep
content hashes, actual revisions, fixture/environment metadata, and capture
commands. Scoped browser captures may use verified contract fixtures; they do
not replace separate real-provider verification or become an E2E dependency.

Use [the task result](../templates/task-result.json) for the retained handoff.
Read [the evidence record format](../references/evidence-format.md) before writing
results or approvals; it defines contract identities, capture metadata,
amendments, and exact-head proof bindings.

```sh
.tkstack/tkstack skills sdlc -- tasks finish \
  --repo <repository> --run <run> --actor <owner-id> --token <lease-token> \
  --task <task-id> --outcome done \
  --head <actual-task-branch-head> --proof <task-result.json>
```

Use `blocked` for an actual blocker and `retry` to release/reopen the owner's
lease. Scheduler records coordinate ownership; they do not replace acceptance
inspection. A reviewed incremental commit unlocks genuine dependents while
unrelated work continues.

## 5. Challenge, mitigate, and reconcile the original workload

Read [review and stacked delivery](../references/review-and-stacks.md). Fan out
independent behavior/contract, correctness/concurrency, and workload-compliance
lenses. Findings have stable IDs, affected requirements, reproduction, severity,
reviewed head, and evidence. Implementers do not approve their own compliance.

Route findings to atomic mitigation nodes. Reproduce the defect red, correct it,
record fresh green proof, integrate the reviewed fix into the affected branch,
and have an independent reviewer close it. Preserve evidence-backed rejections.
Code, contract, dependency, fixture, base, or evidence changes invalidate the
affected checks and verdict; reassess the ready frontier and descendants.

Fill [the review](../templates/review.md) and
[the evidence manifest](../templates/evidence.json). The final reviewer reads the
frozen **initial branch workload** and accepted amendments directly, inspects
the artifacts, and compares every requirement to current observed behavior.
The integration reviewer also reconciles the complete original workload.

`sdlc.py review-digest <evidence.json>` identifies the evidence/compliance payload
the reviewer inspected. Record that digest and the actual reviewer identity in
the approval, then run:

```sh
python3 <skill-directory>/scripts/sdlc.py gate \
  --repo <task-worktree> --baseline <baseline-directory> --manifest <evidence.json>
```

The gate checks exact workload/head bindings, per-requirement check/artifact
coverage, matched contract identities, artifact hashes, appropriate screenshot
pairs, finding dispositions, and independent approval of that exact payload.
It cannot judge artifact meaning or authenticate a fabricated review. The
reviewer must actually inspect and challenge the evidence. Missing or blocked
proof stays incomplete; it is never converted to a convenient waiver.

## 6. Deliver, babysit, and squash the stacks

Publish small stacked PRs from incremental green commits, linking workload,
requirements, dependencies, evidence, and rollback notes. Use installed
`file-pr`, `leaving-pr-comments`, and `babysit-pr` where available; use their
supported native equivalents otherwise. Do not substitute an unrelated
full-autonomy skill with a different trigger or permission contract.

Own each PR through the authorized merge boundary. Monitor current-head CI,
approvals, every existing/new comment, unresolved threads, base drift, and
mergeability. Fix, answer, or reject each concern with evidence; resolve threads
after addressing them. Re-run affected checks and keep required CI green without
weakening it. Reconcile the live host state just before merging and run the
local `gate` with `--merge` against the recorded current-head PR snapshot.

Land dependencies first. Squash each accepted atomic PR into its target so the
default branch retains sparse deliverable history. Save old parent/child heads,
pause writers, then restack descendants with the exact old parent boundary and
observed remote leases after each squash. Revalidate the new diff, evidence,
comments, and CI; use an exact-head merge precondition and respect protections
and merge queues. The stack reference gives the root-first rebase procedure.

Finish with merged PR URLs and squash SHAs, the original requirement-to-evidence
review, mitigation outcomes, and any concrete blocker. Retain artifacts and
old ancestry boundaries until every dependent is delivered; remove owned
worktrees only after their proof and delivery records are safe.
