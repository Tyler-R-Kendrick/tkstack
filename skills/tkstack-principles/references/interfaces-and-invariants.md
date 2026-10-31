# Design the interface around real callers

**Trigger:** introducing a data shape, module boundary, state owner, or public
signature. Describe the caller's task and concrete example before implementation.

The interface includes errors, invariants, ordering, configuration, and resource
behavior, as well as types. Hide useful complexity behind a small surface; avoid
pass-through layers that make callers learn nearly the same implementation.
Use explicit result shapes and state transitions. Parse external data once at
the appropriate boundary; let sound internal contracts carry validated facts.

Concentrate related knowledge so a correction has one owner. Prefer pure
transformations and explicit effects. Consider retry, idempotency, cancellation,
and concurrency ownership before choosing shared mutable state. A real variation
or testable behavior justifies a seam; an imagined future implementation does not.

For a consequential unknown, compare a few whole-interface alternatives or run
a bounded prototype against the same caller/acceptance case. For a settled
mechanical change, reuse the known shape. Repeated workarounds across callers
are evidence to reconsider the interface rather than add more escape hatches.

**Example:** return a typed admission decision with reason and remaining quota
instead of letting every caller interpret mutable counters. **Boundary:** do not
add a decision object to a trivial pure function whose return already expresses
the complete contract.
