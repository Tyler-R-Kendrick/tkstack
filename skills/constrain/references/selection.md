# Choose verification by risk

Apply these hard rules before writing tests. A technique's rigor does not make
it valuable for every feature. Review across layers by the fault each test
catches, not by coverage percentages or test names.

Use the test pyramid as a cost and feedback heuristic: usually place many
fast checks near the behavior they can observe, fewer integration/contract
checks at real boundaries, and a small number of end-to-end checks for risks
that need the full journey. A high-level test may be the cheapest meaningful
check for its contract. Do not force a numerical ratio or remove a boundary
test merely to obtain a pyramid shape. [Test-value review](tests.md) describes
how to rank candidates, measure marginal fault detection and prune safely.

| Method | Valuable scope and required evidence | Reject or consolidate |
| --- | --- | --- |
| Lean proof | Core decision/algorithm invariants and high-risk authorization/authentication logic. Identify the theorem, trusted assumptions, implementation correspondence and run a pinned Lean checker in CI. Required when introducing/changing a consequential core invariant or high-risk auth behavior. | Decorative UI properties, unrelated theorem examples, `sorry`/axiom assumptions of the result, or a model proof with no implementation correspondence. Never count an unexecuted proof as verified. |
| TLA+ / state-machine validation | Discover states, transitions, guards, side effects, ownership and recovery first. Model safety/liveness, concurrent leases, cancellation, retries and crash interleavings when these are consequential. Retain the actual model-checker command, bounds and counterexample checks. | Enumerating every UI state; calling a handful of examples exhaustive; modeling a second implementation without checking correspondence. |
| Property-based | Parsers, normalization, serialization, algebraic invariants and broad structured inputs. Use independent properties, shrinking and retained counterexamples. | Random inputs without an oracle; asserting the implementation against itself; duplicating the same examples under a new framework. |
| Contract + simulation | Default at dependency/integration boundaries. Test both producer and consumer contracts; simulate timeouts, malformed responses, partial failure, authorization denial, rate limits and retries as applicable. | Happy-path-only mocks, call-count assertions on internal choreography, or treating a fake producer as proof of the real provider contract. |
| Functional / BDD | User-visible workflows and distinct cross-boundary failure propagation. Use controlled local dependencies and observable outputs/persisted effects. | Repeating every smaller-layer edge through expensive workflow setup. |
| Model-graded evaluation | Nondeterministic semantic behavior with an independent rubric, reviewed calibration cases, repeated trials and explicit judge/provider. Use `/learn evalify` when available. | Treating a model score or mock grader as proof, or replacing deterministic safety and state checks with a judge. |
| Unit / component | Pure core logic or a specific fault not exposed clearly/cheaply at another retained layer. | Atomic implementation mirrors with every dependency mocked; constants, private choreography, or repeated functional/property coverage. |
| CRAP / hotspot analysis | Locate complex, poorly covered functions for a risk-guided test or refactoring investigation. Review actual behavior and the input coverage report. | Treating a function score as a test-value score, equating execution with a good oracle, or reshaping code only to meet an arbitrary threshold. |
| Performance | A real workload and SLO/resource/deployment limit. Record environment, input scale, warm/cold conditions, repetitions/noise and threshold. Run expensive benchmarks in the appropriate job. | Generic timing assertions, microbenchmarks without product constraints, arbitrary speed targets. |
| Live E2E | A narrow residual risk unavailable through contracts/simulation, such as a provider-specific interoperability probe. Explicit cost, credentials, cleanup and schedule. | Default CI fan-out over live dependencies, exhaustive UI journeys duplicating contracts, or network reliability treated as product correctness. |
| Artifact size | Deployment's actual byte limit and a justified growth allowance on a named built file. | Raising limits to match the current output; claiming source size is deployed bundle size. |
| Structural | Actual package discovery, schema, freshness, licensing and compatibility boundaries. | Source-spelling tests, arbitrary file inventories, repeated lint rules. |

Suite reviews record `kinds` and `overlap` alongside risk, oracle and digest.
For each proposed addition compare the same fault against existing lower and
higher layers; consolidate a demonstrated redundant check when its removal
preserves required risks and no independent boundary, failure localization or
defense-in-depth value justifies it. Contract tests and local filesystem/
process tests here are not live E2E simply because they launch a subprocess.
Do not relabel example-based tests as property-based, or state-transition tests
as TLA+/Lean proof. Risk classification, theorem correspondence, and redundancy
are semantic judgments; the linter enforces declarations and concrete detectable
faults, not the truth of prose. Missing formal verification for a qualifying
changed invariant is unfinished work, not a waiver inferred from passing tests.

When discovering state machines, inspect persisted status fields and enums,
legal-transition checks, lease tokens/expiry, dependency readiness, retry loops,
transaction boundaries and recovery paths. Record one canonical model near its
owning component; do not create a parallel documentation hierarchy. In this
repo, SDLC's durable task/lease/revision store and Learn's candidate/active/
retired steering lifecycle are real state machines. Existing transition tests
exercise examples and concurrency; they are not formal model checking.
