# Test-value review and mutation experiment

The 15 previously reported scenarios were **not established to be orthogonal**.
Five address one host-only policy at different entry points; several Evalify
checks share setup and basic validation. The old 0/3 → 3/3 observations were
before/after checks, not a test-by-fault matrix. They show targeted behavior
changes, not independent contribution or an estimate of all regressions.

## Review of the original scenarios

“Retain” means the inspected behavior is consequential and has a meaningful
oracle or entry-point boundary. It does **not** assert a unique mutation kill
unless noted. Where a scratch probe is named, the previous result was a
measurement scenario, not an additional permanent test. The rows follow the
order in the original report, including the removed structural probe.

| Original scenario | Actual behavior, relationship and decision |
| --- | --- |
| Direct workflow timing | Retain: the runner records operations even when untrusted payload fields resemble control operations; a distinct instrumentation boundary. |
| Fixture and decorator context | Retain: the Constrain CLI must not label different fixtures as proven duplicate tests. |
| Student-t interval | Retain: borderline statistical gains must not be accepted using an understated critical value; separate from the model repetition precondition. |
| Testify descendants | Retain: a generated test deadline must stop its ordinary POSIX descendants. This protects a different execution path from Evalify's own timeout. |
| Model comparison prerequisites | Retain: too few repetitions or zero noise cannot authorize a model-based comparison. This is related to, but exercises a different failure from, the interval calculation. |
| Evalify external executable | Retain the permanent CLI rejection case: it protects the Evalify input boundary. Related to the other host-only cases, not an independent policy. |
| Evolution backend selector | Retain the evolution entry-point boundary. The original check was a scratch probe; the existing permanent preparation test now also rejects the selector and checks that run state stays unchanged. |
| Hill-climb `CommandProvider` symbol | **Remove from the highlighted set:** the scratch probe only checked a symbol's absence. The existing permanent proposer test checks the stronger behavior: an untrusted provider is rejected before a ledger reservation. It is not an extra permanent test. |
| Offline Promptfoo scoring | Retain: the optional real-library integration exercises actual installed assertion processing; the stubbed tests do not establish that integration. |
| Runner model profile | Retain: the runner's configuration boundary must reject a separate model profile. It shares the host-only objective with Evalify and Codify but uses a different entry point. |
| Codify scaffold | Retain: the authoring boundary must reject creating an alternate runtime or model profile. This shares the policy with the previous entries. |
| Compiled inventory | Retain: changing an inventoried reference after compilation must invalidate the artifact; separate from profile selection. |
| Calibration confusion counts | Retain: false positives and false negatives must be distinguishable. The selected Python mutations below do not test the separate JavaScript aggregation calculation. |
| Host timing summary | Retain: actual observations, unknowns, median and maximum must remain distinct. The selected zero-duration fault is uniquely detected by this test in the sampled matrix. |
| Extreme host duration | Retain: overflowing numeric input must fail before offline analysis dispatch. This test alone catches the sampled overflow fault among the five selected tests. |

This review does not establish pairwise orthogonality across the whole suite.
A test with no unique kill in a small sample can still have a distinct oracle
or protect a different boundary; deleting it without evidence would risk losing
behavior. The removed scratch probe remains in the original machine-readable
history for provenance, but is no longer counted as a high-signal result.

## Real fault-to-test matrix

The [machine-readable evidence](2026-11-18-mutation-test-value.json) retains
the fixed plan, engine and runner hashes, original diffs, each individual
baseline and mutant observation, and the decision record. The experiment used
Cosmic Ray 8.9.0 against an exported, clean Git snapshot of Evalify's Python
adapter. No model or separate agent harness was used. Five selected unittest
methods were each run separately against each of five selected mutations. Each
unchanged test was run twice before each matrix. The original and final matrix
were each repeated twice with the same frozen runner, dependency version, plan,
source hash and per-test timeout. A test assertion was reviewed against the
mutated code and failure output before treating it as detection.

The selected tests are: **V**, valid host judgments and offline scores; **R**,
rejected malformed records and model-selection flags; **E**, extreme-duration
rejection; **T**, timing summaries; and **C**, calibration confusion counts.

| Actual mutation | Original detecting tests | Final detecting tests |
| --- | --- | --- |
| Reject a valid zero duration (`>= 0` → `> 0`) | None | T |
| Accept a negative duration (`and` → `or`) | R | R |
| Reject ordinary numeric durations (remove `not` from the boolean check) | V, T, C | V, T, C |
| Accept an unrepresentable duration (`valid = False` → `True`) | E | E |
| Accept a case with an unexpected field (`or` → `and`) | None | R |

The original selected tests detected **3/5** sampled faults in both runs. A
first round adding the zero-duration example detected **4/5**; a second round
adding strict-record examples detected **5/5** in both final runs. All selected
unmodified cases passed their baselines in those runs. The
change also gives each malformed-input subcase its own receipt path, preventing
one accepted invalid input from contaminating a later subcase. It does not add
new Evalify test methods. The matrix shows the valid-duration fault is detected
by three tests, but those tests check different results; it does not justify
removing any of them. Other modules and other possible faults were not included.
The faults and cases were selected in this session, not an independent holdout.

The two baseline and two final runs also recorded durations, but they were not
controlled performance benchmarks: snapshot copying, local system load and an
additional compiled-command probe can affect elapsed time. No latency win or
suite-wide mutation score is claimed. The `assertion_failure` statuses in a
receipt are candidates pending human inspection; timeouts, errors, unrun tests
and invalid mutations must never be counted as kills. A subsequent check using
the revised scoped-snapshot runner hit its 12-second deadline during an
unchanged baseline under concurrent load; it was recorded as `baseline_invalid`
and no mutants ran. It is retained as an inconclusive instrumentation result,
not a test failure or a detection. Final runner verification uses a 30-second
per-test deadline and is recorded separately; it reproduced the 3/5 original
and 5/5 final result once each with the scoped-snapshot supervisor and locked
tool. A subsequent fix extended the total deadline to include setup; its real
engine integration and setup-timeout behavior are checked separately.

For that deadline fix, a deterministic fixture delayed the mutation engine's
version response by two seconds and requested a one-second total budget. The
previous runner continued and completed after 2.64 seconds; the revised runner
stopped the version check and reported the deadline after 1.10 seconds, before
creating a receipt or running a test. This is one controlled timeout probe,
not a claim about production latency.
