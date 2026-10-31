# Interfaces and refactoring

Write a realistic caller example before choosing the interface. Define inputs,
outputs, errors, state ownership, invariants, ordering, resource limits, and the
behavior exposed at the test seam. Prefer a small interface that hides useful
complexity over pass-through wrappers that merely move it.

Inspect callers, callees, current glossary/ADRs, and existing rationale. Make
illegal states difficult to represent and parse untrusted input at boundaries.
Keep factual policy and transformations deterministic. Inject real varying
dependencies without introducing a speculative abstraction for every function.

For a consequential unresolved design, compare a few meaningfully different
shapes against the same caller and acceptance cases. Reuse known patterns for
a settled mechanical change. Diverse-agent exploration is optional and needs
authorized models and isolated artifacts; do not label one model a council.

Examine concurrency before implementation: independent units, private mutable
state, shared-safe caches, capacity, cancellation, and stable fan-in. A canonical
writer justifies a small serialized region. A lock is not the first remedy for
state that did not need sharing.

Keep changes complete across exports, callers, tests, fixtures, documentation,
and migration constraints. Delete dead forms after the real callers move.
Repeated escapes from the agreed shape are evidence to revisit the interface,
not a reason to accumulate casts, flags, wrappers, or one-off branches.

For large mechanical refactors, separate preparation, implementation, packaging,
review, and delivery by actual dependencies. Separate workers require their own
write scopes/worktrees; one release owner coordinates accepted increments.
Preserve the full SDLC workload, COW/sparse, evidence, and stacked-PR guarantees
when that lifecycle is active.
