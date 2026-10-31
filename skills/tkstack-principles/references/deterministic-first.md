# Deterministic first

**Trigger:** designing or reviewing a decision in code, a skill, hook, rule,
workflow, harness, grader, or automation. Minimize the amount of inference
required to reach the correct outcome.

**Reason:** asking a model to repeatedly interpret a rule that could be
implemented directly introduces avoidable variance, cost, latency, and ambiguity.
Explicit inputs, predicates, and state transitions make the decision repeatable,
testable, and suitable for parallel execution.

## Use the least inferential sufficient mechanism

| Order | Mechanism | Examples |
| --- | --- | --- |
| 1 | Deterministic code and explicit rules | Parse an event; validate a schema; evaluate a decision table; compare hashes; query factual API state; enforce a dependency or exit-code gate |
| 2 | Narrow decision model or decision API | A fit-for-purpose classifier, scorer, solver, or decision service for the residual ambiguity, with a defined input/output contract |
| 3 | LLM or agent | Interpret a genuinely ambiguous request or semantic artifact when earlier mechanisms cannot adequately resolve the decision |

A rules engine or solver that deterministically applies an explicit contract
belongs in the first tier. A learned classifier can remain probabilistic even
when narrowly scoped. An LLM hosted behind a “decision API” remains the third
tier. Compare mechanisms by what they actually do, not by their product name.

1. Name the decision, its inputs, available facts, authoritative policy, allowed
   outputs, and failure/unknown states. Reuse an existing contract or helper.
2. Implement factual lookups and objective predicates in code. Prefer types,
   schemas, explicit decision tables, and state machines to free-text branching.
   Keep policy outside generated prose and enforce it at the actual boundary.
3. Separate objective checks from semantic judgment. Resolve the objective
   portion first; send only the unresolved portion to a more inferential tier.
   Do not make an LLM select whether to run a check that must always run.
4. Use a decision model/API only when its scope and measured suitability match
   the unresolved problem. Pin version/configuration where supported, validate
   outputs, and define timeout, cost, confidence/abstention, and error behavior.
   A confidence threshold needs calibration or an explicit task contract.
5. Use an LLM/agent only when the earlier tiers are insufficient. State the
   specific insufficiency in the relevant design/review evidence. Restrict the
   prompt to the unresolved question, require a bounded response contract, and
   validate its output deterministically before applying any effect.
6. Apply the same deterministic policy gate regardless of which tier supplied
   the answer. A model must not convert a missing check, invalid response, or
   unknown state into success. Follow the task's defined fallback or leave the
   decision unresolved; escalate only when a judgment is actually necessary.

## Make execution reproducible

Keep decision functions pure where practical. Pass clocks, seeds, environment,
external observations, and configuration as explicit inputs or retain the
relevant observation/version with the result. Use stable ordering and explicit
tie-breakers, including when workers finish in different orders. Distinguish
replaying captured observations from re-querying mutable remote state.

Represent consequential decisions with an outcome/reason code and relevant
input, policy, and version evidence. Validate preconditions, postconditions,
idempotency, and legal state transitions in code. Enforce required tests,
permissions, and completion criteria structurally instead of relying on an
agent to remember them. Keep the mechanism proportionate to the decision.

Temperature zero, a seed, structured output, and model consensus do not
guarantee deterministic or correct model behavior. A schema validates shape;
it does not establish factual truth or semantic quality. Preserve that boundary
in reports and adoption gates.

## Examples and boundaries

- **PR merge readiness:** fetch current checks, review/thread state, expected
  head, and branch constraints through APIs, then evaluate an explicit predicate.
  Use semantic review only to interpret an unresolved comment. An LLM saying
  “looks green” cannot replace actual check state or merge authorization.
- **Correction learning:** code computes identity, deduplication, provenance
  links, scope matching, and rendering. Abstracting an unfamiliar correction
  into a transferable reasoning rule may need residual semantic judgment;
  keep uncertainty candidate rather than fabricating a deterministic answer.
- **Artifact grading:** code checks coverage, hashes, schemas, and measurable
  contracts. Use a suitable specialized evaluator or actual semantic inspection
  for the remaining visual/meaning judgment. Keyword absence does not prove
  design quality, and no evaluator silently rewrites the rubric to pass.
- **Boundary:** do not invent a brittle approximation of human intent merely to
  remove an LLM call. Keep genuine unknowns explicit. A task asking for creative
  generation can use a generative model; its objective constraints and adoption
  decisions should still use the least inference sufficient for each part.
