# Test value

## Rank a scoped portfolio

Start with the affected behavior and realistic failures, then inspect the
actual assertions, fixtures, helpers and callers. Inventory each candidate by
test ID and layer, supported behavior, fault or invariant, independent oracle,
overlapping tests and boundaries, relevant runtime and maintenance/flakiness
evidence. Record unknowns rather than inventing probabilities or costs. Include
production regressions, risk and change history where available. Derive cases
from input equivalence classes, boundary values, state transitions and failure
paths when relevant. The existing suite-level review record is a starting
point, not a per-test value ranking.

Use this ordering to make the next decision; within a group, consider the
severity and likelihood of the risk, the strength and independence of the
oracle, demonstrated marginal fault detection, confidence in the evidence,
and the measured cost of keeping the test:

1. **Protect:** coverage of required safety, security, compatibility, recovery,
   and other consequential contracts, including independently useful boundary
   or defense-in-depth checks. A smaller layer is not automatically equivalent.
2. **Strengthen or investigate:** important risks with missing, weak or
   uncertain evidence, including flaky tests whose behavior is worth preserving.
3. **Consolidate or prune candidates:** tests with no meaningful observable
   behavior, tautological or implementation-derived expectations, or proven
   overlap where the remaining suite preserves the relevant contracts.

This is a review priority, not a universal numerical score or a deletion rule.
When risk, detection, or overlap is unknown, investigate before deleting. The
same risk can justify checks at multiple layers when they catch different
failures, exercise an independent boundary, or provide useful diagnosis.
For a repeatable ordering within a group, sort first by the project's assessed
risk (high, medium, low), then by demonstrated distinct fault or boundary
coverage and evidence confidence. Where the retained behavior is equivalent,
prefer the lower measured cost; investigate expensive removal candidates first.
Use the test ID as a stable tie-breaker. Keep unknown evidence marked unknown,
and explain the ordering rather than adding incomparable numbers into a score.

## Measure the value that can change

For a bounded, risk-selected slice, freeze the code, test selection, runner,
environment and a set of plausible faults from incidents or deliberately seeded
regressions. Verify the unchanged suite passes and the fault actually changes
the intended behavior. Run the relevant tests against each isolated fault and
restore the implementation. Record which tests detect which faults, and whether
failures reflect the intended oracle rather than setup errors or timeouts.
Compare the **retained suite** with and without a candidate: report faults
detected / relevant faults tried, critical risks still exercised, and any lost
or newly detected faults. A unique kill is useful evidence, but zero unique
kills does not prove a test is worthless: two tests can detect the same fault,
and neither is unique until the other is removed. The fault sample is not all
future defects.

Where tooling exists, use targeted mutation testing to discover survivors and
coverage to find unexecuted code. Classify equivalent, invalid and unproductive
mutants with reasons; do not write brittle tests merely to kill them. Report the
scope and denominator of any mutation result. Coverage, mutation score, CRAP
(complexity combined with coverage), test count, and suite bytes are signals,
not proofs of correctness or interchangeable units of value. A timeout, crash,
unrun test or failed harness is not automatically a valid mutant kill.

Measure end-to-end suite wall time under comparable CI conditions, including
parallelism and setup, with repeats when noise matters. Record available
flakiness and maintenance evidence separately; do not sum per-test times as a
claim about parallel CI or invent maintenance hours. Report measurement gaps.
For unit tests, the traditional FIRST qualities (fast, independent,
repeatable, self-validating, timely) are useful maintenance diagnostics. The
classic timely rule favors writing tests before production code; for agents,
evaluate the actual resulting tests and feedback, even if fine-grained human
TDD cadence is not followed. These qualities do not replace a meaningful oracle.

## Use UB Mode's quality signals

The pinned UB Mode skill combines behavior-first tests with Crapper, Mutator
and Dryer. Apply these as a sequence of review signals, not as interchangeable
test-value scores:

1. **Make it work.** For a concrete behavior change, start with an independently
   expected result and, where practical, see a targeted test fail for the
   intended reason before implementation. If an honest automated test is not
   practical, use appropriate evidence rather than inventing a weak test.
2. **Find risky functions.** With Crapper or an equivalent tool, review the
   highest-risk functions and their actual callers and coverage. The CRAP
   formula is `CC² × (1 − coverage)³ + CC`, with coverage as a fraction and
   CC the cyclomatic complexity. For example, CC 10 at 50% coverage scores 22.5;
   even at 100% it scores 10. A high score suggests a candidate for a useful
   behavioral test, simpler control flow, or both. CRAP ranks *functions*, not
   individual test utility; executed lines and a low score do not prove a
   meaningful oracle. UB Mode specifies a score below 10, but adopt a threshold
   only when the project has justified and calibrated it. Do not split coherent
   code or add tautological tests solely to satisfy the number.
3. **Investigate uncovered code and survivors.** With Mutator or an equivalent,
   start on the changed, risk-relevant scope and verify a green baseline. For
   each meaningful survivor, reproduce the behavioral gap, then add or improve
   the cheapest independent oracle that catches it. Review equivalent,
   invalid, unreachable and unproductive mutants instead of forcing kills.
   Before deleting dead code, inspect actual callers, extension points and
   supported compatibility; lack of coverage alone is not proof of dead code.
4. **Review duplication and refactor.** Dryer reports structurally similar
   code for review; a similar shape does not prove the same behavior or justify
   collapsing boundaries. Its documented default excludes test/spec directories,
   so do not claim it evaluated test redundancy without checking actual
   discovery. For real refactoring, pin observable behavior, make the structural
   change, then rerun relevant checks and fault probes.

Read the installed tool's version and actual report before using its numbers.
For the companion versions documented by their maintainers, Crapper may report
missing coverage or a failed coverage command as zero, while `--no-coverage`
leaves CRAP unavailable; investigate those cases instead of treating either as
measured test quality. Mutator reports a timeout or non-compiling mutant as a
kill, excludes uncovered sites from its killed/(killed + survived) score, and
may reuse earlier killed results. For a before/after pruning comparison, rerun
the same relevant mutants against each test selection, including previously
killed mutants (for example with `--mutate-all` when supported), and validate
the failure reason. An aggregate report does not by itself attribute a kill to
an individual test. Record uncovered sites and the exact denominator separately.

These companion tools are optional and are not bundled with Constrain. Their
installation and coverage runs can create environments, install dependencies,
run tests, and replace reports; inspect the version's behavior before use. A
missing tool is missing evidence, not a successful measurement.

For example, consider these **illustrative**, not measured, results:

| Test | Fault detected | Median isolated time | Review |
| --- | --- | ---: | --- |
| A, unit | Discount calculation | 8 ms | Keep the cheaper observed check. |
| B, unit | Discount calculation | 12 ms | Investigate consolidation with A. |
| C, contract | Provider timeout | 150 ms | Protect its distinct boundary. |

If the matched suite runs take 170 ms before and 158 ms after removing B, the
sampled fault count remains 2/2 and the observed difference is 12 ms. Repeats
are still needed to judge timing noise. The sample does not establish that A
and B are equivalent for untried faults, or that C is redundant because both
layers exercise checkout.

## Improve and prune in bounded rounds

1. Freeze the baseline, fault set and runner; record passing results, timing,
   risk coverage and known noise. Reserve genuinely independent faults or cases
   for confirmation when available. Set a time budget, objective, guardrails
   and a meaningful improvement threshold before changing the suite.
2. Choose one hypothesis: strengthen a weak oracle, move a case to a cheaper
   sufficient layer, consolidate an overlap, or remove a proven no-value test.
   Preserve required risk and boundary checks. Change one coherent thing at a
   time; record the candidate and rationale.
3. Repeat the same fault matrix, relevant regression tests and cost measurement.
   Keep a change only if the measured benefit exceeds noise and the guardrails
   hold; otherwise restore the prior suite. Compare the fixed winner with the
   original on reserved cases when possible. With no independent cases or a
   weak signal, describe the result as exploratory, not a proven improvement.
4. For each removal record the intended behavior, replacement or reason it no
   longer matters, retained evidence, and remaining uncertainty. Remove
   test-only production helpers only after checking their actual callers and
   supported interfaces. A test asserting absence can still protect a security,
   migration or compatibility contract; obsolete implementation facts alone
   are candidates for removal.

For an explicitly requested measured optimization, follow the installed
hill-climb workflow if available. These steps guide a human/agent review; the
Constrain checker does not execute this loop or infer semantic test value.

## Agent-written code and agent systems

For code produced by agents, obtain expected behavior from an independent
requirement or example, not solely from the same agent's implementation and
tests. Review consequential acceptance examples (Gherkin can help when useful)
and exercise the actual system.
Agent-written unit tests, targeted mutation, boundary simulations and human
inspection complement each other; neither a rigid human TDD cadence nor an
arbitrary CRAP threshold is a substitute for the evidence.

When the system under test is itself an agent, add representative multi-step
tasks with real tool effects or safe simulations. Grade the final observable
outcome, and inspect traces for required safety, authorization or side-effect
invariants without requiring one arbitrary route. Separate task, selection and
untouched confirmation cases; run repeated trials for nondeterministic behavior
and report success, variability, cost and latency. Calibrate any model grader
against reviewed examples; deterministic checks verify facts where possible.
An answer claiming success is not proof the environment reached that state.

## Existing checks and review records

For each test, state the realistic fault, public behavior or invariant, expected
observation, and its distinct contribution or justified overlap. Read the assertion
and its fixture, not just its name. Rejection, atomicity, CLI exits, persisted
state, isolation and recovery are valuable behaviors. Assert independent output
or effects; a mocked call alone ordinarily repeats implementation.

Prefer the least expensive layer that exercises the intended risk. Extend an existing test
or parameter table for variants sharing setup and contract. Separate tests when
a distinct failure needs isolation. Do not create a test to check that a file,
heading, function, dependency, or constant exists unless its presence is itself
a supported discovery or compatibility contract and you exercise that contract.
Avoid source substring assertions, snapshots of incidental wording, and redoing
a linter's work. Generated artifacts need consumer/freshness checks, not one
assertion per generated file. No test-count or coverage target is a value metric.

The deterministic Python AST rules reject constant oracles, self-comparisons,
identical executable test bodies in the same fixture context with the same
signature and decorators (ignoring names/docstrings), and tests with no visible
assertion. A body shared by different fixtures or parametrizations is a review
candidate, not proof of redundant behavior. Helper-owned assertions need an exact, reasoned exception;
no glob exceptions. Stale exceptions fail. Rules are deliberately narrow:
assertion presence does not establish its independence or adequacy. The current
adapter discovers Python unittest-style functions with `test_` names in the
configured patterns; pytest fixtures, inherited tests, dynamically generated
tests, and other languages require a verified adapter before claiming coverage.

`.constrain/reviews.json` maps every discovered suite to `sha256`, `risk`, and
`oracle`. The hash binds the review to actual bytes; risk describes the failure
class, oracle describes observed outputs/effects. Review each changed test and
its helpers, then compute only that suite's SHA-256. These are editable review
records, not authenticated approvals. Never grandfather an entire suite just
because it currently passes. Delete or strengthen noise; preserve actual faults.

Validate with an isolated, reversible production fault and a focused retained
test that must fail; restore the implementation and rerun. Include an unrelated
good fixture, known-bad fixtures, legitimate exceptions and a final unseen fault.
Do not run arbitrary repository tests merely to lint them. Run the real suite
separately when verifying behavior, with its dependencies and explicit time limit.

## Initial tkstack audit

The pre-change offline baseline was 376 tests (10 opt-in tests skipped), passing.
The suite review inventory records each suite's actual methods, regression
risks, behavioral oracles and cross-layer overlap. Cleanup removed six tests:
source-spelling installer checks already covered by executable bootstrap tests;
a YAML shape check plus its private fallback parser; a source-substring CI
check; duplicate pinned vendor inventory; and a duplicate shared-helper byte/
reference check already enforced by check_skills; and a duplicate marketplace
file/identity checklist covered by package/manifest conformance gates. Six behavioral tests cover the
new constraint gates and external target installation. Count alone is not the
improvement metric: focused fault sensitivity and retained boundaries are.

Retained overlaps have different boundaries: Codify owns frozen execution;
command-schema owns typed CLI/API dispatch; normalization owns their integration
across real packages. SDLC graph/head validation and durable-store restart/
transaction tests assert different invariants. Mock subprocess/clock failures
exercise external failure contracts; they are not wholesale internal mocks.
There is no blanket deletion of unit/component tests based on size or labels.

Local CLI/filesystem/Git workflows are contract/functional simulations, not live
provider E2E. Optional judge/provider checks remain opt-in. The repo has no
owned application login flow, Lean/TLA+ suite, randomized property framework,
performance workload or deployment binary. No formal-proof or performance
result is claimed. State-transition cases are example-based; the selection
rules require a real proof/model and implementation correspondence for a newly
changed qualifying core or high-risk invariant. Do not add a decorative proof
to inflate assurance or treat this inventory as a completed formal audit.

The constraint test fixtures run outside the source repo without importing test
code. Two unchanged runs passed. In isolated copies, disabling constant-oracle
detection, review-drift detection, index reading, or growth checking made the
retained tests fail. A separately selected deployment-ceiling fault also failed.
All five faults were detected, and the source implementation was preserved.
This is focused mutation evidence, not a universal mutation-score claim.

## Sources and limits

- [UB Mode, pinned skill](https://github.com/unclebob/ub-mode/blob/3da62bf3fcfd2034de41f30d920d2739e566171f/SKILL.md)
  supplies the behavior-first, Crapper, Dryer and Mutator workflow. The companion
  [Crapper](https://github.com/unclebob/crapper), [Mutator](https://github.com/unclebob/mutator)
  and [Dryer](https://github.com/unclebob/dryer) READMEs document their current
  reports and limits; those separate tools are not part of the pinned snapshot.
- [caldoai/prune-tests](https://github.com/caldoai/skills/blob/main/skills/prune-tests/SKILL.md)
  motivates checking whether assertions depend on intended behavior. Its
  blanket rules about duplicate tests and tests of absence are not safe to
  apply without the boundary and contract checks above.
- [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
  describes layered feedback as a heuristic, not a mandated ratio.
- [Google on mutation testing](https://testing.googleblog.com/2021/04/mutation-testing.html)
  explains unproductive mutants; [research on suite reduction](https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1085&context=csetechreports)
  shows that reduction can compromise fault detection.
- In [a September 2026 interview](https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code),
  Robert C. Martin describes unit tests, CRAP and mutation feedback for agents,
  plus human behavioral checks. In [another account](https://productengineers.com/episodes/season2/why-hardcore-technical-focus-still-matters-big-time-uncle-bob/),
  he still requests tests first but has not found fine-grained human TDD steps
  reliable for agents. His evolving thresholds are personal practice, not a
  project-independent policy.
- [Anthropic's agent eval guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  distinguishes trials, trajectories and real outcomes.
