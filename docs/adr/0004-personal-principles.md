# Load personal principles from one portable package

Status: accepted. Date: 2026-10-30.

The user wants tkstack-owned principles modeled on Pstack's principle structure,
starting with the least possible inference and concurrency throughout code.

Keep a root `skills/tkstack-principles` package with a short index and complete
references for deterministic-first decisions and concurrency by design.
Prefer code/rules, then specialized decision models/APIs, then LLMs/agents;
evaluate the actual mechanism rather than its transport. Concurrency uses
explicit dependencies, bounded resources, isolated mutation, and stable fan-in.

The full installer creates one shared `.agents/principles` link independently
of which harnesses are selected. Native Codex/Claude instruction blocks and
Cursor's always-applied rule load this index. Install the same package as a
normal skill and publish its self-contained root in the marketplace catalog.
Preserve explicit preference evidence and scoped rules in the existing learn
ledger; do not introduce another evidence store or edit vendor snapshots.

Structural installation checks verify package/link/pointer integrity. Actual
policy enforcement belongs at each executable decision boundary and concurrency
invariant. Do not substitute keyword lint or claimed model determinism for
semantic correctness, and do not represent instruction loading as behavioral
evaluation or a measured performance improvement.
