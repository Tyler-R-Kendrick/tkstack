# Trace a system

Start from the question's entrypoint: a command, request, event, scheduled job,
or public function. Inspect repository manifests, current instructions, relevant
glossary/ADRs, and tests. Find symbols with `rg` or the harness's native search;
read implementation rather than inferring behavior from names.

Trace input validation, caller/callee edges, transformations, state ownership,
effects, error propagation, and the observable output. Include ordering,
idempotency, cancellation, and bounded concurrency when they affect the answer.
For a placement question, identify the existing owner and which callers would
need to understand a new interface. Prefer the seam that concentrates knowledge.

For broad questions, split discovery by independent dataflow or subsystem. Bound
concurrent reads and reconcile conflicting findings against the same revision.
Do not create delegates for a small question; delegation needs actual permission
and available capabilities. A file inventory alone is not a working model.

Explain the user's flow first, then the concepts required to understand it.
Introduce an unfamiliar term before relying on it. Link the few files that let
the reader continue. A small diagram helps only when relationships need one.
Architecture critique is a separate requested output: first explain the current
shape, then identify concrete failing cases and tradeoffs.

When search unexpectedly misses a known file, inspect ignore rules, scope,
encoding, and binary detection. A scoped `rg --text` or byte inspection can
settle that uncertainty without scanning unrelated private files.

Done when the path from trigger to effect is grounded, the non-obvious invariant
is explained, and every consequential assertion has current source evidence.
