# Test value

For each test, state the realistic fault, public behavior or invariant, expected
observation, and why another retained test would not catch it. Read the assertion
and its fixture, not just its name. Rejection, atomicity, CLI exits, persisted
state, isolation and recovery are valuable behaviors. Assert independent output
or effects; a mocked call alone ordinarily repeats implementation.

Keep the least expensive layer that detects the fault. Extend an existing test
or parameter table for variants sharing setup and contract. Separate tests when
a distinct failure needs isolation. Do not create a test to check that a file,
heading, function, dependency, or constant exists unless its presence is itself
a supported discovery or compatibility contract and you exercise that contract.
Avoid source substring assertions, snapshots of incidental wording, and redoing
a linter's work. Generated artifacts need consumer/freshness checks, not one
assertion per generated file. No test-count or coverage target is a value metric.

The deterministic Python AST rules reject constant oracles, self-comparisons,
identical executable test bodies (ignoring names/docstrings), and tests with no
visible assertion. Helper-owned assertions need an exact, reasoned exception;
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
