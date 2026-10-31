# Tkstack principles

The canonical personal principles live in
[`skills/tkstack-principles`](../skills/tkstack-principles/SKILL.md). The index
routes to five conditional references, following Pstack's index-and-principle
structure while keeping this package independently owned and portable.

1. [Deterministic first](../skills/tkstack-principles/references/deterministic-first.md):
   use deterministic code and explicit rules wherever sufficient, then narrow
   decision models/APIs, then LLMs/agents for residual judgment. Facts, routing,
   required checks, state transitions, permissions, and objective completion
   gates should be executable rather than repeatedly inferred from prose.
2. [Concurrency by design](../skills/tkstack-principles/references/concurrency-by-design.md):
   design all code for safe parallel composition and bounded throughput.
   Identify dependencies, isolate mutable state, define capacity and failure
   handling, and make results stable across completion orders. Serialize only
   the smallest region required by a concrete constraint.
3. [Smallest complete change](../skills/tkstack-principles/references/minimal-complete-change.md):
   preserve the full requested outcome while removing unnecessary machinery.
4. [Interfaces and invariants](../skills/tkstack-principles/references/interfaces-and-invariants.md):
   design around actual callers, concentrated ownership, and meaningful seams.
5. [Evidence and context](../skills/tkstack-principles/references/evidence-and-context.md):
   verify actual outcomes and load detailed context only for its stated trigger.

The first two are explicit user preferences. The additional three are curated
adaptations requested from the installed catalog; they are not invented user
correction evidence. See [source selection](skill-distillation.md).

These apply to application code and to skills, hooks, rules, workflows, agents,
and harness configuration. They guide new work and changes to existing code;
they do not require an unrelated wholesale rewrite before making a small fix.
Current instructions and explicitly selected workflows still govern scope.

An API is a transport, not a determinism guarantee. Reading structured CI state
can be a factual operation; an LLM decision endpoint remains the last tier.
Versioned models, schemas, seeds, and temperature zero alone do not establish
repeatable or correct semantics. Split objective checks from unresolved meaning
and validate any model-produced output before effects.

Parallelism also needs a real mechanism. Independent reads can be batched;
workers need bounded queues and owned state; a single canonical ledger needs
its existing writer protocol. A pure parser can stay synchronous and safely
serve concurrent callers. Required ordering and benchmark integrity remain
valid constraints. Concurrent execution must preserve deterministic fan-in.

## Loading and distribution

The full installer provides `.agents/principles` as a shared link to the
canonical package, including for a Claude-only or Cursor-only installation.
Codex and Claude native instruction blocks point at its `SKILL.md`; Cursor's
always-applied steering rule uses the same project/home path. Each selected
harness also receives the `tkstack-principles` skill in its normal skill folder.
Pstack's `poteto-mode` and upstream principles remain unchanged.

```sh
python3 scripts/install.py --target . --dry-run
python3 scripts/install.py --target .
python3 scripts/doctor.py --target .
```

The root marketplace also distributes this self-contained Markdown package.
For a standalone skill installation, add a pointer to that installed package's
index in the harness instructions when automatic loading is desired. Full
dotfiles installation creates the shared link and native pointers automatically.

The user's exact request is preserved as a `preference` in the shared learn
ledger, with two active personal reasoning rules that point back to these
principles. It is not labeled an observed assistant mistake. Future revisions
retain provenance and explicit scope rather than silently broadening a rule.

## Verification boundary

The installer deterministically verifies source/link identity, installs one
shared package, and maintains marked native pointers without replacing unrelated
instructions. Tests cover partial-harness routing, reference resolution,
idempotency, and clean removal. These checks establish loading/configuration;
they do not prove an agent followed a principle during every task.

At implementation boundaries, enforce objective decisions with code, contracts,
types, state machines, and meaningful checks. For concurrency changes, verify
the relevant invariants under controlled overlap/failure and measure performance
when claiming a gain. A universal keyword scanner cannot establish semantic
correctness or safe parallelization, so this change adds no such proxy gate.
