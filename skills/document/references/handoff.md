# A resumable handoff

Read the actual worktree, branch heads, task artifacts, and current checks.
The handoff is a current state record, not a fabricated transcript.

Persist working/session handoffs at `.tkstack/sessions/<session>/document/handoff.md`,
with the local ignore policy initialized. Requested published documentation
keeps its intended destination; private handoff bookkeeping stays under `.tkstack/`.

Include:

- User outcome and exact remaining scope, with the original workload reference.
- Repository/worktree, base and current heads, dirty paths, and ownership.
- Completed work with evidence; distinguish written, checked, merged, deployed,
  and measured outcomes.
- Open decisions, blockers, failed attempts, and why a tempting retry would fail.
- One concrete next action, its prerequisites, and commands already known to work.
- Active task/lease IDs, isolated outputs, shared caches, PR relationships,
  running process/session IDs, and which worker owns monitoring.
- Authorization already established and actions outside the requested boundary.

Use short pointers to canonical requirements, contracts, logs, and evidence
instead of copying every artifact. Preserve secrets by using credential names
and approved selectors, never values. Mark missing or stale context.

Handoff does not automatically launch another agent. Before a real ownership
transfer, stop or join owned work, hand off watchers explicitly, and ensure only
one writer retains each mutable task. A paused task is not complete. Resume by
checking observed state against the handoff, since heads and CI may have moved.
