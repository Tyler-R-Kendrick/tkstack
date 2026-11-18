# Verify behavior at meaningful seams

Start with the requirement and the public behavior or real contract being
proved. Reuse a runner that exercises that path. Preserve the intended red,
implement the smallest green, then refactor under the meaningful checks.
The user's BDD/contract strategy remains the acceptance policy.

Expected values come from a worked example, requirement, independently known
result, or reference implementation. Do not reimplement the production algorithm
inside an assertion, snapshot whatever happens to be produced, or check private
call ordering that has no public obligation. A passing test that cannot detect
the stated failure is not useful evidence.

## Select a check by the fault it can detect

Name the promise in client terms, a plausible fault, and the observable difference
between a legal execution and a faulty one. Start with the cheapest existing
public seam that exercises the mechanism. For framework choice, evals, TLA+
and Lean, use [testing strategy and tradeoffs](testing-strategy.md). Use the
project's existing runner and honor any applicable Constrain policy.

| If the behavior depends on | Exercise | Keep independent evidence for |
| --- | --- | --- |
| An independently released API or event | Run the consumer client and actual provider against the same pinned interactions and supported versions. Pact can replace journeys that only detect incompatible requests or responses. | An acknowledgement can precede persistence or delivery. Observe the promised effect at the owning component. Probe deployed wiring only for an explicit deployment obligation. |
| A law over values | Enumerate a small finite domain or generate structured inputs with an independent property. Sorting must preserve the input multiset as well as order. Shrink failures and pin important rare cases. | A round trip can hide a shared encoder/decoder error. Retain specified wire vectors, contractual examples and distinct incident regressions. |
| A sequence of actions | Drive the real component with generated commands and compare observations to a small independent state model after each action. | Use the real engine for process contention, crash rollback or redelivery. A sequential model can pass while a real concurrent transaction fails. |
| Two competing events | Force both legal orders. Start with a fake clock, a controlled callback or a failpoint. Check the deadline just before, at, and after expiry. | Use a real scheduler, load run or adapter when the claim depends on resource pressure, synchronization or actual I/O. |
| Many interacting clocks, faults or retries | Simulate only the boundary needed. Exercise the production protocol and check client-visible histories. | Name the schedules, storage/transport behavior and dependencies left outside the model. For a finite formal model, record its bounds and check implementation correspondence. |

Challenge a proposed property with a deliberately degenerate implementation.
A sorter that always returns an empty list satisfies ordering, and a no-op
normalizer satisfies idempotence. Supply an independently expected effect or
a conservation law and make the property fail on the defect before replacing
examples. Count the input class actually exercised, especially with filtered
generators. Keep named boundary cases deterministic.

## Decide whether to retire a test

Where both tests execute the implementation, compare them on the same known
defect and correct build. For a type or proof that prevents constructing the
defect, show the rejected construction or failed theorem and establish its
correspondence to the shipped path. One shared mutant demonstrates sensitivity
to that fault only. Pin any required example that random generation might
miss on a PR. For executable comparisons, inspect why each goes
red. If only the old test fails, keep it and repair the replacement. If only the
new test fails, inventory the old test's other obligations before removing it.
When both detect the fault, retire the more expensive one if its boundary,
contract examples and useful failure localization are covered. Otherwise narrow
it to its distinct obligation. If neither fails, fix the oracle or fixture.
Record the observations and decision in the existing review rationale.

## Check histories and progress

Derive the oracle from the promised consistency model. Record operation start,
completion and unknown outcome separately. After a lost acknowledgement a write
may already have committed. For safety, check the observed history under that
model. A fixed tie-breaker can hide a race on every seed. If an acknowledgement
and timeout are both ready, exercise each first while preserving causal and
transport ordering. For recovery, state which faults heal, which may persist,
and what new work must succeed within the bound. A timely success establishes
progress on that trace. Claiming eventual progress over all admissible traces
also requires a temporal argument and explicit fairness assumptions. A stalled
cluster can still appear converged.

Calibrate a checker with an independently legal history and a known violation.
A valid counterexample contradicts the checked property even when the process
exits successfully. Verify how the checker represents false and unknown. A checker timeout, unknown verdict or unreached
target leaves acceptance inconclusive. An indeterminate client operation is a
valid input whenever the operation may have committed. For replay, retain
the minimized actions and order of competing events, reached condition,
client-visible history and checker verdict together with the seed, build,
configuration and model version. Run fixed regressions on PRs. Budget broader
searches separately and retain their minimized counterexamples. See the optional
[checker verdict evidence](evidence-format.md#checker-backed-requirements).

## Inspect artifacts at the actual boundary

For screenshots, match viewport, data, theme, state, and revision. Inspect the
images themselves. For a CLI/TUI, use the real terminal interface when terminal
behavior is the requirement. Capture HARs, traces, or recordings only when they
prove a relevant obligation; redact secrets and identify capture commands.
These captures complement BDD/contracts and do not require an E2E suite.

Distinguish a launcher failure, missing dependency, empty capture, skipped path,
or stale artifact from product failure or success. Re-read generated deliverables
and compare exact formats when the requirement makes those formats meaningful.

Use verified, contradicted, or inconclusive findings with their exact scope.
Compilation proves compilation. Mock-host validation proves that host's simulated
contract. Neither proves deployment, UI quality, model improvement, or a complete
workflow. Keep semantic inspection separate from mechanical receipt checks.

When deciding how to enforce an invariant, first use a type/constructor or
compile-time check that rules out invalid states. Parse untrusted runtime data
at its boundary. When Learn is installed, use `/learn lintify` for recurring static source rules,
`/learn testify` for a distinct behavioral regression, `/learn hookify` for
an observable tool event, `/learn skillify` to package a reusable procedure,
and `/learn codify` to freeze executable workflow code. Where installed, apply Constrain for
repository budgets and verification selection. Combine them only for distinct
gaps, and do not test the same type guarantee again as an implementation mirror.
