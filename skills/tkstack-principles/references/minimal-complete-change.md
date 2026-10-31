# The smallest complete change

**Trigger:** choosing implementation scope, dependencies, abstractions, or a
refactor. Finish the authorized outcome with the least unnecessary machinery.

Map every required caller, export, fixture, check, and configuration change
before judging the diff's size. A short incomplete fix is not simpler for its
next user. Reuse the repository's established solution, then the standard
library/platform, then an existing suitable dependency before adding machinery.

Look up existing code assets before reproducing a pattern. At three verified
occurrences, or before a requested third use, follow `reusify` when available
and create/use the smallest suitable reusable asset within scope. Preserve
meaningful variation; raw similarity does not establish a shared invariant.

Remove dead paths and speculative options when they obstruct the change and
their removal is in scope. Prefer a direct readable expression over a wrapper
that hides no useful complexity. Do not split by line count or add configuration
for an imaginary consumer. Keep business logic and side effects easy to trace.

Preserve validation at trust boundaries, error handling that protects data,
accessibility, compatibility obligations, and actual user requirements. A known
shortcut needs its real limit and upgrade condition; it is a defect when the
supported workload crosses that limit.

**Example:** reuse the existing request validator and migrate all actual callers
instead of adding a second validator for a new endpoint. **Boundary:** a shared
API's supported compatibility period may justify temporary parallel forms;
record the reason, owner, and removal criterion rather than deleting it blindly.
