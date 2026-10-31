# Build the instrument before climbing

Name who notices the improvement and what changes for them. Map that outcome to
one primary metric with quality, correctness, cost, and scope guardrails. Reuse
a real instrument where possible; avoid a proxy that can improve by omitting work.

Record a compact loop card: outcome, current baseline/revision, instrument and
observed output, noise, practical keep threshold, guardrails, data splits, budget,
stop rule, and evidence location. Reuse the existing plan template rather than
creating a second authoritative measurement format.

Demonstrate that the instrument can distinguish a real failure or known control.
Inspect captures yourself. Verify that traces show actual execution, cases ran,
and the output contains the expected work. A launch error or empty agent trace
cannot establish a model's behavior, even if a grader assigned a number.

Repeat unchanged measurements to estimate relevant variance. Choose repetition
counts from the workload, noise, and budget; do not copy an upstream benchmark's
sample size or keep percentage as universal policy. Timed experiments may need
isolated measurements even when preparation is parallel.

For each attempt, keep one causal hypothesis, comparable control, observed work
counts, and both accepted and rejected results. Preserve the frozen grader and
untouched confirmation. A sensitivity failure requires a new declared baseline,
not a quieter criterion that lets a preferred candidate pass.
