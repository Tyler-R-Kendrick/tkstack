# Choose verification for a requirement

Start with the decision the evidence must support. What would a user observe
if the change were wrong? Which inputs, event orders or environments matter?
Find an existing check that would fail for that reason. Extend its fixture or
table if that covers the change. When an existing constraint already excludes
the fault, point to it and test the remaining boundary. BDD describes the
behavior, a property or example supplies inputs and expectations, and the
execution boundary determines which production mechanisms are exercised.

## Choose a method and framework

| Question | Start with | Escalate or stop when |
| --- | --- | --- |
| Does this input produce the specified result or effect? | A named example or parameter table in the project's unit/component runner. Use BDD examples at the public boundary for acceptance. | Use types, constructors or static analysis for a statically decidable rule. Check parsing and persisted effects where external values enter. |
| Does a law hold over many values or actions? | Exhaust a small finite domain. Otherwise use a property/state-machine runner such as Hypothesis or fast-check, with an independent oracle and shrinking. | Keep named contract boundaries and minimized defects. Use a simple example when there is one exact regression. |
| Can independently released components communicate and complete the promised work? | Verify the consumer and real provider against pinned interactions across supported versions, including rolling upgrades and rollback. Exercise effects against the owning component or real adapter. | Untested version pairs remain unknown. Use a narrow deployed probe for a separate wiring obligation. A change inside one component rarely warrants adding a contract framework. |
| Does quality hold across a population of tasks? | A representative eval with labeled cases, a deterministic scorer or calibrated rubric. | Use the eval procedure below when results depend on the mix of cases or judgment. One fully specified local output usually needs an assertion. |
| Could a legal interleaving violate the protocol? | Force a known pair of event orders. For a consequential protocol with interacting transitions, check a bounded state model with TLC or an equivalent explorer. | Use simulation for actual scheduling seams and recovery. Keep real concurrency or crash tests for assumptions about the runtime. |
| Must a consequential rule hold for every valid value or trace? | State the theorem and its assumptions. Prove it in Lean when the obligation warrants it or repository policy requires it. | Keep an implementation correspondence check. For an unchanged rule, reuse its proof and run affected boundary checks. |
| Does an experience or resource meet a concrete target? | Use a matched visual/accessibility check or an instrumented benchmark on the relevant workload and environment. | Keep real rendering, assistive technology, load or hardware in the check when the claim depends on it. Virtual time cannot measure tail latency. |

Choose tools after the method. Prefer the installed runner, fixtures and CI
job. Adopt a framework when a missing capability such as shrinking, schedule
exploration or proof checking earns its setup, feedback time and maintenance
cost. Where project policy requires a method, budget for it.

## Evals for judgment and distributions

Use an eval when many outputs may be acceptable, a ranking or error rate
matters, or a model, prompt, skill or retrieval change may help one class of
users and hurt another. For example, use exact assertions for a search API's
response schema and an eval for whether it ranks relevant results first.
Freeze representative cases and critical slices, expected labels or rubric,
baseline, candidate, thresholds and cost. Calibrate a human or model judge on
independently labeled good and bad answers. Prefer executable scoring when
possible. Compare on matched inputs. Repeat noisy trials and report errors,
denominators and observed variation. If noise masks the gain or the grader
cannot distinguish calibrated cases, report the comparison as inconclusive.
Hold fresh confirmation cases outside tuning. Keep hard correctness obligations
as separate pass/fail checks.

An eval can consolidate subjective golden-output comparisons. Preserve exact
examples for contractual wording or wire bytes. A green average can hide a
failing mandatory slice. For a deterministic bug with one specified answer,
extend the normal regression test and skip the extra eval. See [measured
feature work](measured-feature-work.md) for the existing harness and stop rule.

## TLA+ for interacting transitions

Model when correctness depends on which actor acts next across retries, crashes,
cancellation, recovery or ownership changes. Identify initial states, actions,
guards and the invariant. For eventual progress state what must eventually
happen, which failures may persist, and what fairness or delivery assumptions
allow progress. Pin the spec, checker version and configuration. Record the
number of modeled actors, queue depth and data bounds. Check that the configuration actually
selects the named `INVARIANT` or temporal `PROPERTY`, that intended states are
reachable, and that the run completed.
Retain completion status and counterexample traces. Drive a known bad transition
through the model and replay its trace or compare allowed transitions with
observations from the actual implementation.

A completed exhaustive TLC run covers the reachable states of that configured
finite model. A sampled run or an interrupted search has a different scope.
One operation succeeding within a deadline after healing shows bounded recovery
on that execution. A general liveness claim requires checking the temporal
property under the stated assumptions. Handwritten schedule permutations can
be retired where the model covers them and the implementation correspondence
survives. Keep tests for database locking, lost messages, persistence and
adapters that the model abstracts. A sequential formatter or a single known
timeout boundary seldom earns a protocol model.

## Lean for universal invariants

Use a kernel-checked theorem when a broad input domain or an inductive rule
makes examples insufficient for a consequential guarantee. In projects governed
by TKStack Constrain, introducing or changing a consequential core invariant
or high-risk authentication/authorization behavior requires Lean evidence.
Scope the theorem to the changed rule. An unrelated UI change that calls an
unchanged decision does not create a new proof obligation. Outside a required
proof boundary, prefer a type, exhaustive decision table or ordinary test when
it fully covers a modest rule. If a required theorem or its correspondence
cannot be checked, leave that obligation open.

Identify the production rule, theorem, domain, preconditions and trusted
assumptions. Check that its premises can hold and that they do not assume the
conclusion. Run the exact declaration with a pinned Lean toolchain, inspect
its axiom dependencies and reject unfinished proofs such as `sorry` or an
axiom asserting the desired result. Tie the proof to running code through
a shared verified definition, a checked refinement, or a differential bridge
that compares the real implementation to the proved definition. State whether
the bridge is sampled, exhaustive over a finite domain, or formally proved.

For a reservation service, Lean can prove that a successful reservation preserves
a capacity bound for all natural-number amounts under an atomic transition.
TLC can explore two competing reservations when reading and writing are separate
steps. A concurrent database test checks whether the real transaction supplies
the assumed atomicity. If the implementation uses fixed-width integers, verify
overflow behavior or enforce the range assumed by the proof. A proof can
displace duplicate arithmetic examples over its proved definition. A finite
bridge to a separately written implementation still needs regression coverage
for that implementation and its boundaries.

## When a check becomes redundant

Compare the obligation, domain, observable boundary and fault. For a model or
theorem, weaken the relevant rule, inspect the counterexample or failed proof,
then show how a corresponding production fault is detected. A production mutation
can leave a model and its proof green. A score on held-out examples cannot
discharge a universal theorem. Compare maintenance and feedback time. Preserve a cheap example
when it uniquely localizes a regression or documents a contract. Put fast
deterministic cases on PRs and give larger campaigns a budget and trigger.
Rerun required gates when their inputs change. [Fault comparisons and replay](behavioral-verification.md#decide-whether-to-retire-a-test)
