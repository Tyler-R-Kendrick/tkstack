# Independent review, evidence, and stacked delivery

Read this reference when a task branch reaches review, when a PR needs
mitigation, or when landing a stack. The coordinator owns the dependency graph,
PR lifecycle, and final compliance decision. Workers own their assigned changes.

## 1. Pin the review inputs

Before work starts, freeze each branch's initial workload and record its hash,
baseline Git SHA, requirement IDs, BDD scenarios, contract boundaries, expected
evidence, ownership paths, and dependency IDs. Preserve those original bytes.
An approved scope change is a separate dated amendment with its reason and
affected IDs; it does not erase an unmet initial requirement.

At review time record the candidate head SHA and exact dependency heads. Give
reviewers the initial workload, amendments, diff against the intended PR base,
contract results, and evidence manifest. A narrative completion summary cannot
replace these inputs.

## 2. Fan out adversarial review

Dispatch independent reviewers with fresh context and read-only access to the
candidate. Use separate worktrees when their checks generate files. Keep their
findings independent until each returns:

- **Behavior and contracts:** try to violate Given/When/Then outcomes, reject
  malformed requests, break consumer expectations, and expose compatibility
  changes using real provider/consumer verification.
- **Correctness and integration:** inspect the complete affected flow, task
  dependency assumptions, migration behavior, races, failure paths, and the
  code outside the diff that consumes the changed interface.
- **Workload compliance:** compare the initial workload requirement by
  requirement against the actual evidence, including negative scenarios and
  each applicable HAR, screenshot pair, recording, or diagnostic artifact.

One reviewer can cover several lenses when the workload is small. Preserve
independence from implementation and state the concurrency actually used. A
missing reviewer, unavailable model, or timed-out review is not approval.

Require findings with stable IDs, affected requirement IDs, severity, exact
head SHA, source or artifact location, and a reproducible claim. Reviewers must
distinguish a demonstrated failure from a hypothesis. They do not edit the
candidate, change its acceptance criteria, or merge it.

## 3. Mitigate, then verify the disputed behavior

The coordinator deduplicates findings by failure mechanism without dropping
their evidence. Record each as open, mitigating, resolved, or rejected-with-
evidence. Assign a mitigation worker its own task, ownership paths, dependencies,
and isolated worktree. Independent mitigations can run concurrently; overlapping
writes and changes to a shared contract are serialized by their owners.

For a real defect, add or select a failing BDD/contract case first, make the
smallest correction, collect the new green result, and commit it incrementally.
The coordinator integrates the reviewed mitigation commit into the affected
task branch and reruns its proof; a fix existing only on a mitigation branch
does not resolve the original candidate.
The reviewer then checks that the original failure is closed at the new head.
For a rejected finding, retain the specific counterevidence and reason. A new
product requirement becomes an explicit workload amendment and graph update.

Any code, contract, fixture, dependency, configuration, or base change invalidates
the affected proof and review verdict. Re-run affected checks and recapture the
affected runtime evidence. Keep the old artifacts with their original revision;
do not relabel them as captures of a newer build. A reviewer may record a
mechanical equivalence argument for unchanged evidence, naming the old and new
heads, relevant tree/configuration identity, and why the requirement is unaffected.
That argument does not replace required CI on the current head.
The strict local gate requires fresh exact-head check and candidate-artifact
records. Keep an equivalence argument as supplemental review evidence; it
does not bypass those bindings or justify relabeling an old capture.

## 4. Close the workload compliance gate

Use the [review template](../templates/review.md). An independent reviewer must inspect artifacts and
check results, not merely count files in a manifest. Match the manifest's
`workload_sha256` and `head_sha` to the frozen workload and candidate under
review, then verify every initial requirement and accepted amendment.

Every requirement has a pass, fail, or blocked verdict and links to the
check IDs and artifacts that prove it. An inapplicable artifact type needs the
workload's applicability decision and rationale. A missing or newly waived
requirement cannot be turned into a pass by updating the implementation summary.
Check before/after provenance, artifact hashes, relevant environment/fixtures,
and any required retention/access links.

Final approval requires a complete requirement-to-evidence matrix, passing
required BDD and contract checks at the current head, resolved findings or
evidence-backed rejections, and an independent compliance verdict bound to
that workload/head pair. Structural manifest validation is necessary but is
not a semantic judgment that an artifact proves a requirement.

## 5. Publish incremental commits as stacked PRs

Keep the atomic, verified checkpoints as incremental commits while developing
and reviewing. Create a small PR for each deliverable; its description links
the workload, requirement IDs, parent PR, other dependencies, proof, and rollback
or mitigation notes. Use `file-pr` and `leaving-pr-comments` for their formatting
discipline where available.

The work graph is a DAG; a GitHub PR has one base branch. Record those separately.
Independent roots target the repository's default branch. A child can target
one parent task branch to expose only its incremental diff. Additional graph
dependencies remain explicit merge prerequisites. For a join needing several
unmerged implementations, wait for those prerequisites or use a separately
owned integration task with its own workload; do not quietly pull sibling
patches into a supposedly atomic PR.

Publish draft PRs as soon as a verified slice exists. Record all task branches,
PR URLs, current heads, intended bases, and dependency state in the graph. A
green child still waits for required code dependencies to land, report-only
gates to be accepted, and proof against the resulting base. Review/report nodes
are retained with their owning PRs; they do not require artificial code PRs.

## 6. Babysit every PR through its current head

The coordinator owns one watcher per PR. Use Tstack's `babysit-pr` and its
`pr-wait` helper, or the harness's supported PR watcher; do not create competing
poll loops. Read existing CI, reviews, and comments before waiting. Stay active
until the PR is merged or a concrete blocker prevents further authorized work.

Reconcile **all** review comments and unresolved threads across all pushes.
Page through general PR comments, inline review comments, review submissions,
and review threads; these are separate host collections. Use the host's
pagination/cursors so an early or truncated page cannot hide old concerns.
An old comment is not closed merely because a newer commit exists. Classify
each as a required fix, question answered, resolved by an identified commit,
rejected with counterevidence, non-actionable acknowledgement, or an explicit
scope amendment. Reply where an explanation is owed and resolve a thread only
after its concern is actually addressed. Keep the local finding/comment ledger
in sync. Waiting for green does not replace reading new comments.

Fix failing checks and real findings in incremental mitigation commits. Separate
code failures from infrastructure flakes, retry transient failures within the
repository's policy, and keep required checks green without weakening them.
Each push restarts the affected evidence/review gates. Before merging, reread
the exact head and base, current comments, required approvals, required checks,
mergeability, merged code dependencies, and accepted report gates. Respect branch protection and merge
queues; no administrator bypass or ignored human change request.

Invoking this skill for an implementation task carries only that task's
authorized publication and merge scope. A request to create the skill itself
does not authorize posting comments, opening PRs, or merging this repository.
When the task includes landing the work, keep babysitting through the observed
merge; otherwise stop at a reviewable, explicitly identified boundary.

## 7. Squash the stack from its roots

Use one squash commit per accepted atomic PR, retaining requirement and evidence
links in the final commit/PR record. This keeps intermediate commits available
during review while the default branch records the sparse deliverables. Land
only nodes whose dependencies have actually merged, in topological order.

Squash merging changes commit identity. Before merging a parent, save its
reviewed head, every child's current head, the child's old parent head, and the
observed remote head used for the push lease. Pause workers on branches being
restacked. After the parent is confirmed merged, fetch the real squash commit
from the default branch and verify its result.

For each direct child, replay only the child's own commits onto the new parent
result from inside its worktree:

```text
git -C <child-worktree> rebase --onto <new-parent-head> <saved-old-parent-head>
git -C <child-worktree> push --force-with-lease=refs/heads/<child>:<observed-remote-head> origin HEAD:refs/heads/<child>
```

The placeholders are values recorded from this stack, not branch names to guess.
The old boundary is the saved parent head that the child actually inherited.
Rebasing the entire history onto the squash commit without that boundary would
replay already-merged parent changes and duplicate the stack.

Restack descendants in order using their saved **old** parent heads and each
parent's newly rewritten head. Retarget a direct child's PR to the default
branch after its parent lands; deeper children retain their immediate task
parent until that parent lands. Check the resulting PR diff for duplicate or
missing patches, recollect invalidated proof, and wait for current-head green
and review again. Force-with-lease is limited to the workflow's owned branches;
a failed lease means stop and reconcile the concurrent update.

Only remove a task worktree and branch after its commits, evidence, and PR
outcome are retained and no descendant still needs its old boundary. Finish
by checking default-branch CI, the merged requirement/evidence record, and that
every graph node is delivered or explicitly blocked. Report merged PRs and
squash SHAs, compliance evidence, mitigations, and any real remaining blocker.
