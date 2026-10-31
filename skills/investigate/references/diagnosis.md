# Diagnose from a real signal

First distinguish product failure from failed observation. Verify the process
started, the intended code path ran, and the artifact contains meaningful work.
Empty traces, zero API/tool calls, or a launcher error do not reveal agent
behavior. A missing runtime is a setup failure, not a failing product test.

Reuse the smallest instrument that observes the exact symptom: a public-seam
test, deterministic command, provider/consumer contract, request replay, PTY,
or scoped browser capture. Record the command, revision, fixture, environment,
and observed failure. Prefer BDD/contracts for acceptance; visual evidence does
not require introducing an E2E suite. Captured traces may support a bounded
diagnosis when live reproduction is unavailable; state that limit.

Minimize a reproducing input while preserving the same failure. For a race,
record attempts and failures, isolate clocks/seeds/resources where feasible,
and use barriers or controlled schedules before arbitrary sleeps. A flaky
reproduction remains probabilistic; do not promise deterministic success.

List the few plausible causes and a prediction that separates each one from
the alternatives. Inspect only the code and instrumentation needed to test
those predictions. Change one causal variable per probe. Use a debugger or
tagged boundary logs; remove temporary instrumentation after an authorized fix.

For performance, capture an unchanged baseline and meaningful work counters
before optimizing. Check caches, warmup, contention, and the actual critical
path. Use `hill-climb` when the request is sustained measured optimization;
ordinary diagnosis does not start a search or spend model budget.

When a fix is authorized, preserve a red case at the real failing seam, apply
the smallest complete correction, and verify green on both minimized and original
scenarios. A single-caller test cannot prove a multiple-caller bug is gone.
If no suitable seam exists, report the gap rather than manufacturing a test.

Return cause versus hypothesis, evidence, original symptom status, and untested
conditions. Missing access is a concrete blocker; it does not justify an invented
root cause or asking the user to perform every observation manually.
