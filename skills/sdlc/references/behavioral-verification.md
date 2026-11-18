# Verify behavior at meaningful seams

Use the requirement's public behavior or real contract. In the project's
runner, demonstrate the intended red, implement the smallest green and
refactor under the meaningful checks. The user's BDD/contract acceptance
policy governs. Derive the expected result from a requirement, worked example,
independently known value or reference implementation. Copying production
logic, snapshotting its current output or checking private call order can
allow the same defect on both sides of the assertion.

## Select a check by the fault it can detect

Use [testing strategy and tradeoffs](testing-strategy.md) for the cheapest
adequate seam, framework choice, task evals, TLA+ and Lean. Challenge a
proposed property with a degenerate implementation. A sorter returning an
empty list satisfies ordering; require preservation of the input multiset.
A no-op normalizer is idempotent; check the specified transformation too.
A round trip can hide a shared encoder/decoder error. Retain published wire
vectors, mandated examples and distinct incident regressions. Shrink failures,
count the input classes actually exercised (especially with filtered
generators) and pin important boundaries for deterministic PR coverage.

## Decide whether to retire a test

Compare executable checks on the same historical defect or reversible fault
and the same correct build. Inspect why each goes red. For a type or theorem
that prevents constructing the defect, show the rejected construction or
failed proof and tie it to the shipped path. One mutant demonstrates
sensitivity to that fault only. Where Constrain is installed, `native mutate`
can compare selected Python unittest cases against the same bounded Cosmic Ray
mutations. Inspect each outcome before drawing a retirement conclusion.

| Detects the fault | Decision |
| --- | --- |
| Old only | Keep the old test and repair the replacement. |
| New only | Inventory the old test's other obligations before retiring it. |
| Both | Retire the more expensive check if boundary, contract examples and useful failure localization are covered. Otherwise narrow it to its distinct purpose. |
| Neither | Repair the oracle or fixture. |

Record the observed comparison and decision in the review rationale. Keep
fast fixed regressions on PRs; budget larger searches with a trigger, retain
minimized counterexamples and rerun required gates when their inputs change.

## Check histories and progress

Derive the oracle from the promised consistency model. Record invocations,
completions and indeterminate outcomes. A timed-out write may have committed;
include that possibility in the history. A fixed tie-breaker can hide a race
on every seed. If acknowledgement and timeout are both ready, force each first
while preserving causal and transport order. Check just before, at and after
the deadline. For recovery specify which faults heal or persist and which
new work must succeed within the bound. A stalled cluster can look converged.

Calibrate the checker with an independently legal history and a known violation.
Inspect its actual return value: a valid counterexample contradicts safety
even after a successful process exit. Distinguish `false` from an unknown
verdict; checker timeout or an unreached target leaves acceptance inconclusive.
Retain minimized actions and event order, reached condition, client-visible
history and checker verdict with the seed, build, configuration and model
version. [Checker verdict evidence](evidence-format.md#checker-backed-requirements)

## Inspect artifacts at the actual boundary

Inspect screenshots with matched viewport, data, theme, state and revision.
Use a real terminal for promised CLI/TUI behavior. Capture HARs, traces or
recordings only for a relevant obligation; redact secrets and identify the
capture command. These captures complement BDD/contracts without requiring
a full E2E suite. Re-read generated outputs and compare exact required formats.

Distinguish setup failures, missing dependencies, skipped paths and empty or
stale captures from product outcomes. Classify findings as verified,
contradicted or inconclusive at the observed boundary. Compilation confirms a
build; mock-host checks exercise the simulated contract. Inspect behavior
before claiming deployment, UI quality, model improvement or workflow success.

When Learn is installed, use `/learn lintify` for static rules, `/learn testify`
for distinct regressions, `/learn hookify` for tool events, `/learn skillify`
for reusable procedures and `/learn codify` for frozen executable workflows.
Apply installed Constrain budgets and verification policy. Add a mechanism
only for a distinct gap.
