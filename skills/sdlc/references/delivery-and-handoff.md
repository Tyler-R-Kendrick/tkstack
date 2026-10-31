# Deliver and preserve intent

Record actual base/head commits, scope, dirty work, and branch ownership before
delivery. A local-only or review-only ask stays at that boundary. Existing merge
authorization persists; a workflow name or green CI does not create a new grant.

Keep PRs small coherent increments with behavior, requirements/evidence,
dependencies, relevant checks, and material risk. Draft the description for a
reader who did not see the conversation. Avoid a chronicle of abandoned attempts.

One owner monitors each PR. Prefer a supported event watcher; otherwise use the
host's supported bounded polling with a shared API budget and backoff. Do not
start duplicate watchers or busy loops. Preserve the exact last observed head,
checks, unresolved threads, base, and rate-limit state across resumes.

On each meaningful event, batch fresh reads and disposition every outstanding
concern. Verify bot claims against source; fix or explain with evidence. Older
unresolved comments still need a disposition even if they predate the latest
push. Do not weaken CI to finish. Revalidate affected work on the new head.

Modernize intent as well as ancestry. Compare the PR's goal with the current
base and competing/landed solutions. Recommend rebase, rework, or obsolescence
with evidence before pushing. Preserve another writer's work; use an isolated
worktree for dirty active checkouts. Rewriting requires an observed remote lease.

For active SDLC stacks, preserve the root-first squash/restack and exact-head
gates in the existing stack reference. A watcher wake is an event, not permission
or proof that merging is safe. Keep merged, deployed, and measured states distinct.

A handoff records original scope, current heads/worktree, completed evidence,
failed attempts, remaining obligations, watcher/lease ownership, and one concrete
next action. It does not launch a new agent or transfer a writer lease silently.
Report meaningful progress or a blocker through the current authorized channel.
Do not send external status messages just because a source skill does so.
