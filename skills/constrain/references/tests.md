# Test value

## Rank a scoped portfolio

Inventory the affected tests by ID and layer. Inspect assertions, fixtures,
helpers and callers. Record the public behavior, plausible fault, independent
oracle, overlap, and measured runtime, flakiness or maintenance cost. Use
production incidents, change history, input classes, boundaries, transitions
and failure paths to identify gaps. The suite-level inventory starts the review.

1. **Protect** required safety, security, compatibility and recovery checks,
   including independent boundaries or defense in depth.
2. **Strengthen or investigate** important risks with weak or uncertain
   evidence, including valuable flaky tests.
3. **Consider consolidation or removal** for tautologies, implementation
   mirrors, unobservable behavior and demonstrated redundant coverage.

Within each group order by project-assessed risk (severity and likelihood:
high, medium or low), then distinct fault or boundary coverage and evidence
confidence. Prefer the cheaper equivalent check and investigate expensive
removal candidates first. Use test ID to break ties. Keep unknowns explicit
and investigate them before deletion. Document independent diagnosis or
boundary coverage that justifies overlap. This ordering does not assign a
numeric value or authorize automatic deletion.

## Measure the value that can change

Freeze the risk-selected code, tests, runner, environment and plausible
incident or seeded faults. Establish a green baseline. For each isolated fault
confirm the behavior changed, run relevant tests, inspect the failure and
restore the code. Compare the retained suite with and without the candidate.
Report detected/relevant faults tried, critical risks exercised and any lost
or new detection. Two tests can share every kill until one is removed.

Use coverage to find unexecuted paths and targeted mutation to find survivors.
Classify equivalent, invalid and unproductive mutants with reasons. Report
scope and denominator. A setup error, timeout, crash or unrun test alone
cannot establish a kill. Coverage, CRAP, counts, suite bytes and mutation
scores measure different things. The bounded Python/unittest workflow follows;
use the appropriate native tool for other projects.

## Run a bounded Python mutation matrix

On POSIX systems with non-reaping `waitid`, Constrain's `native mutate` executes selected mutations with the maintained
[Cosmic Ray](https://github.com/sixty-north/cosmic-ray) Python mutation tool.
It does not install a tool or run mutations as part of the read-only `check` or
`audit` gate. Install the supplied hash-locked `requirements/requirements.lock`
into a private virtual environment with a bounded installer, for example:

```sh
python3 -m venv .tkstack/mutation-env
timeout 180s .tkstack/mutation-env/bin/python -m pip install --require-hashes \
  -r skills/constrain/requirements/requirements.lock
```

The lock pins Cosmic Ray 8.9.0 and its runtime distributions. The tool checks
the reported version, not the authenticity of the executable; trust the local
installation and review acquisition separately. Some pinned source distributions
need build tooling: isolated build dependencies and network access during
installation are outside this runtime lock. The experiment itself never installs
dependencies or selects a model or agent harness.

Choose a small risk-relevant slice. Cosmic Ray's `init` and `dump` identify
operator names, occurrence indexes and source positions for a module; these are
relative to that exact source. For example, put the following configuration in
an ignored scratch directory, substitute the absolute module path, then run the
bounded commands. `init` inventories mutations; it does not run the test command.

```toml
[cosmic-ray]
module-path = '/absolute/project/path/to/module.py'
timeout = 10.0
excluded-modules = []
test-command = 'python3 -m unittest tests.test_example'
[cosmic-ray.distributor]
name = 'local'
```

```sh
timeout 30s .tkstack/mutation-env/bin/cosmic-ray init /path/to/config.toml /path/to/session.sqlite
timeout 30s .tkstack/mutation-env/bin/cosmic-ray dump /path/to/session.sqlite > /path/to/mutants.jsonl
```

Inspect the positions and pick plausible independent faults, not just a high
score. Prepare a JSON plan with fully qualified **individual unittest method**
IDs and selected `core/` operators and occurrence numbers from that inventory.
For each mutant, include the source file's `source_sha256` to fail closed if
the indexed module changed; omitting it leaves that compatibility check to the
reviewer. For example:

```json
{
  "version": 1,
  "tests": ["tests.test_example.ExampleTests.test_behavior"],
  "mutants": [{"id": "boundary", "module": "src/example.py", "operator": "core/ReplaceComparisonOperator_GtE_Gt", "occurrence": 0, "source_sha256": "replace-with-actual-lowercase-sha256"}]
}
```

Commit tracked changes in the selected Git checkout first: experiments export
exactly `HEAD`, ignore untracked files and fail on tracked dirt. Test and
mutation paths must exist in that snapshot. Use the project's test dependencies
with the Python interpreter that invokes the command; ignored local assets are
not copied into the snapshot. Run with an unused receipt path:

```sh
.tkstack/tkstack skills constrain -- native mutate \
  --repo /absolute/project --plan /absolute/plan.json \
  --engine /absolute/project/.tkstack/mutation-env/bin/cosmic-ray \
  --output /absolute/project/.tkstack/mutation-receipt.json
```

For a standalone install, call `python3 <installed-skill>/scripts/mutate.py`
with the same flags. Two clean baseline repetitions precede any mutants;
defaults are 15 seconds per test and 300 seconds total, including engine and
Git setup, configurable within the documented bounds. Once inputs are validated
and an unused receipt is reserved, a setup deadline is recorded as
`setup_timeout` with elapsed time and no mutant results. Earlier input or output
path failures are reported on standard error. The compiled host has its own outer deadline. Each
case receives a private snapshot under the selected workspace's scoped
`.tkstack/sessions`; ordinary POSIX child processes are stopped as a group.
Git discovery in each test is capped before the enclosing checkout. A detached child, blocked filesystem, remote side effect, or
descendant in another process group is not guaranteed to stop; use an appropriate outer
supervisor and isolation for untrusted tests. Project tests and the trusted
local engine can have effects outside the snapshot; this is not an OS sandbox.

The new JSON receipt includes the commit, plan, runner and source hashes, engine version and launcher hash, Python
version, actual mutant diffs, per-case elapsed time and captured output. A
`passed` cell is a candidate survivor; `assertion_failure` is a **candidate**
kill until its actual output and mutated behavior are reviewed. `error`,
`timeout`, `setup_timeout`, `not_run_or_skipped`, `not_run`, `invalid_mutation`, and
`engine_timeout` are not kills. A `complete` run means all selected cells were
attempted, not that all faults were valid or detected. A failed baseline
prevents mutant execution. Never classify a test as redundant solely from one
sample, and preserve distinct boundary protections when removal evidence is
incomplete. Retain the plan, receipt and review rationale together.

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

The pinned UB Mode workflow uses the following signals in order:

1. **Make it work.** Derive the expected behavior independently. Where
   practical, observe a targeted failure before implementation. When an
   automated check is impractical, inspect the actual behavior.
2. **Find risky functions.** Crapper ranks functions by
   `CC² × (1 − coverage)³ + CC`, where CC is cyclomatic complexity and
   coverage is a fraction. CC 10 scores 22.5 at 50% coverage and 10 at 100%.
   Review callers, control flow and assertions. UB Mode's target below 10 needs
   local calibration. Splitting coherent code or executing it without an
   independent oracle gives a misleading improvement.
3. **Investigate survivors.** From a green baseline, run Mutator on changed
   risk-relevant code. For meaningful survivors, reproduce the gap and
   strengthen the cheapest sufficient oracle. Explain equivalent, invalid,
   unreachable or unproductive mutants. Check callers, extensions and supported
   interfaces before treating uncovered code as dead.
4. **Refactor real duplication.** Review Dryer's structural matches against
   observable behavior. It excludes test/spec directories by default. Verify
   discovery before using its results for test consolidation. Pin the behavior
   and rerun checks and fault probes after refactoring.

Inspect the installed versions. Crapper can report missing or failed coverage
as zero, while `--no-coverage` leaves CRAP unavailable. Mutator counts timeout
and compile failure as kills, excludes uncovered sites from killed/(killed +
survived), and can reuse earlier kills. Re-run the same relevant mutants on
each selection, including previous kills (`--mutate-all` when supported).
Review cell failures before attributing kills to tests. Record uncovered sites
and the denominator. These optional tools are separately installed. Acquisition
or coverage runs may install dependencies, execute tests and overwrite reports.
Mark missing tool evidence unknown.

Illustrative portfolio: unit tests A (8 ms isolated median) and B (12 ms) both
catch a discount fault. Investigate consolidating B into A. Protect contract
test C (150 ms) for its distinct provider-timeout observation. If matched suite
runs take 170 ms with B and 158 ms without, the observed gain is 12 ms with
2/2 sampled faults still detected. Repeat for timing noise and check untried
obligations before deletion.

## Improve and prune in bounded rounds

1. Freeze the baseline, runner and faults. Record passing behavior, risk
   coverage, timing and noise. Set an objective, budget, guardrails and minimum
   gain. Reserve independent confirmation cases where available.
2. Change one thing: strengthen an oracle, move to a cheaper sufficient
   boundary, consolidate overlap or remove a no-value check. Record the
   hypothesis and candidate.
3. Repeat the same fault matrix, regression and cost checks. Keep gains above
   noise with guardrails intact; otherwise revert. Confirm the fixed winner
   against the original on reserved cases. Label weak or unconfirmed evidence
   exploratory.
4. For removals, record the behavior, replacement or obsolescence, retained
   evidence and uncertainty. Check callers and interfaces before deleting a
   test-only helper. Tests of absence can protect security, migration or
   compatibility obligations.

For requested measured optimization, use the installed hill-climb workflow
when available. The mutation command measures the selected cells. The invoking
agent reviews the portfolio and owns iteration and keep/revert decisions.

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
and report success, variability, cost and latency. Use the invoking agent for semantic grading and calibrate its judgments
against reviewed examples; deterministic checks verify facts where possible.
Do not launch another model or agent harness.
An answer claiming success is not proof the environment reached that state.

## Existing checks and review records

Assert observable outcomes such as rejection, persisted effects, atomicity,
CLI exits, isolation or recovery. Extend an existing test or parameter table
for shared contracts; separate distinct regressions when isolation helps.
Source strings, incidental snapshots, repeated lint and internal mock calls
rarely establish public behavior. A file, heading, dependency or constant
earns a check when exercised as a discovery or compatibility contract.
Verify generated artifacts through their consumer and freshness checks.

The Python AST checker rejects constant oracles, self-comparisons, missing
visible assertions and identical executable bodies within the same fixture,
signature and decorators (ignoring test names/docstrings). Different fixtures
or parametrizations can justify identical bodies. Helper-owned assertions need
an exact, reasoned exception. Glob or stale exceptions fail. The adapter
discovers Python unittest-style `test_` functions in configured patterns.
Verify an adapter before claiming coverage for pytest fixtures, inherited or
dynamic tests, or other languages. An assertion's presence does not establish
oracle quality.

`.constrain/reviews.json` binds each discovered suite to its `sha256`, `risk`
and `oracle`. Inspect changed assertions and helpers, repair weak checks, then
refresh only the reviewed suite digest. These editable records document review
and do not authenticate approval.

Use a reversible production fault, focused failed check, restored green, an
unrelated good fixture, known-bad fixtures, legitimate exceptions and a final
unseen fault. Run behavior tests separately with their dependencies and time
limit. Lint does not execute arbitrary repository tests.

## Initial tkstack audit

The original offline suite passed with 376 tests (10 opt-in skips). The review
inventory recorded methods, faults, oracles and cross-layer overlap. Six
deletions covered installer source spelling already exercised by bootstrap,
YAML shape plus its private fallback parser, a CI source substring, duplicate
pinned vendor inventory, shared-helper bytes/references enforced by check_skills,
and marketplace identity covered by manifest conformance. Six behavioral tests
exercise the new constraint gates and external target installation.

Retained distinct coverage included Codify frozen execution, typed command-schema
dispatch and normalization across real packages; SDLC graph/head validation and
durable-store restart/transactions; and subprocess/clock failure contracts.
Local CLI/filesystem/Git runs exercise functional and contract behavior. Live
judge/provider checks stayed opt-in. The original inventory had no owned login
flow, formal suite, randomized property framework, performance workload or
deployment binary. Later hill-climb TLC configurations, Lean theorems and bridge
tests cover its controller. SDLC transition examples cover another component.
See the current [selection policy](selection.md) for changed invariants.

External constraint fixtures did not import test code. Two unchanged runs
passed. Isolated faults disabling constant-oracle detection, review-drift
detection, index reading and growth checking all failed their retained tests,
as did a separately selected deployment-ceiling fault. All five faults were
detected without changing the source implementation.

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
