# Choose verification for a requirement

Name the client-visible promise, a plausible fault, the observable difference
and the inputs, event orders or environments where it matters. Extend an
existing fixture if it exercises that mechanism. If a constraint already
excludes the fault, cite it and check the remaining boundary. BDD describes
the promised behavior; examples and properties can both exercise it.

## Choose a method and framework

| Obligation | Cheapest useful check | Remaining boundary |
| --- | --- | --- |
| One specified output or effect | Use a simple example when there is one exact regression. Extend a public component test or parameter table. Use a type, constructor or static rule if it excludes the fault. | Parse external values and observe promised persisted effects. |
| Law over values or action sequences | Enumerate a small finite domain or generate structured inputs with shrinking (e.g. Hypothesis or fast-check). For sequences, drive the real component and compare each action to an independent state model. | Challenge vacuous properties, count reached input classes and pin contractual or rare examples. [Property checks](behavioral-verification.md#select-a-check-by-the-fault-it-can-detect) |
| Independently released API or event | Verify the consumer and real provider against pinned interactions across supported versions, including rolling upgrade and rollback. Pact can replace compatibility-only E2E journeys. | Untested version pairs remain unknown. An acknowledgement can precede persistence or delivery. Observe the effect at its owner. Use a deployed probe for a separate wiring obligation. |
| Timing or concurrency | Force a known race with a clock, callback or failpoint. For many interacting faults, drive production protocol logic in simulation and check client-visible histories. | Identify excluded schedules, storage and transport behavior. Use the real engine for process contention, crash rollback and redelivery. Virtual time cannot measure tail latency. |
| Quality, performance or user experience | Use a task eval for rankings or judgment, a benchmark for a workload/SLO, or a matched visual or accessibility check. | Use real rendering, assistive technology, load or hardware when the claim depends on it. |

Prefer the project's runner, fixtures and CI job. Add a framework when a
missing capability, such as shrinking, schedule exploration or proof checking,
earns its setup, feedback time and maintenance. Budget for required methods.

## Evals for judgment and distributions

Use an eval when multiple outputs are acceptable, a ranking or error rate
matters, or a model, prompt, skill or retrieval change may help one population
and harm another. Check search response shape directly and evaluate relevance
over queries. For a fully specified regression, use the direct assertion.

Freeze representative cases and critical slices, independent labels or rubric,
baseline, candidate, thresholds and budget. Prefer executable scoring. Calibrate
human or model judgments on known good and bad outputs. Compare matched inputs,
repeat noisy trials and report errors, denominators and variation. Hold fresh
confirmation cases outside tuning. An insensitive grader or noise masking the
gain makes the result inconclusive. An eval can replace subjective wording
snapshots; keep mandatory per-case contracts, exact wire vectors and required
slices as separate gates. If Learn is installed, `/learn evalify` supports
judgments by the invoking agent and offline assertion scoring. [Measured feature work](measured-feature-work.md)

## TLA+ for interacting transitions

Choose bounded state exploration with TLC or an equivalent checker when the
order of retries, crashes, cancellation, recovery or ownership changes can
violate a consequential protocol. A changed label or single known deadline
usually needs an example. Define initial states, actions, guards and safety
invariants. For progress, specify the temporal property, persistent failures
and fairness or delivery assumptions. Pin the spec, tool and configuration,
including actor, queue and data bounds. Verify the intended `INVARIANT` or
`PROPERTY` was selected, the target state was reachable and the run completed.

A completed exhaustive TLC run covers the reachable states of that configured
finite model. Distinguish sampled or interrupted searches. A single timely
success demonstrates bounded progress on its trace; general liveness requires
checking the temporal property under the stated assumptions. Weaken a transition
to elicit a counterexample. Save the trace and replay it against production
code, or compare implementation transitions with the model. Retire schedule
permutations only within that correspondence. Keep runtime checks of locking,
persistence, delivery and adapters that the model abstracts.

## Lean for universal invariants

Use a kernel-checked theorem for consequential universal or inductive claims.
TKStack Constrain requires Lean evidence for a new or changed consequential
core invariant or high-risk authentication/authorization behavior. For an
unchanged rule, reuse its proof and run affected boundary checks. Outside
required proof scope, use a type, exhaustive table or ordinary check when
sufficient. Leave a required theorem or correspondence open until verified.

Identify the shipped rule, exact theorem, domain, preconditions and trusted
assumptions. Check that premises can hold without assuming the conclusion.
Run the declaration under pinned Lean, inspect its axiom dependencies and
reject `sorry` or an axiom asserting the result. Connect proof to executable
code via a shared verified definition, checked refinement, or differential
comparison against the proved definition. State whether this bridge is
sampled, exhaustive over a finite domain or formally proved. A sampled
comparison leaves an implementation regression obligation.

For reservations, Lean can prove conservation for all natural-number amounts
under one atomic transition. TLC can explore two reservations whose reads
and writes may interleave. A real database test checks the transaction's
atomicity. Verify fixed-width overflow or enforce the range assumed by the
theorem. Preserve parsing and adapter checks outside its typed domain.

## When a check becomes redundant

A finite eval cannot discharge a universal theorem. A theorem about a model
can stay green after a production mutation. Compare the promised behavior,
domain, mechanism and fault before retiring the old check. [Fault comparison
and retirement](behavioral-verification.md#decide-whether-to-retire-a-test)
