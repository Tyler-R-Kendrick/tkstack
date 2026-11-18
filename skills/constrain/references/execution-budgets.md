# CI and execution

Choose fixed workload, cache conditions and meaningful work first. Budget job
count, deadlines, worker capacity, network access, and costly optional tests;
separate performance measurement from correctness checks. Do not shorten a run
by dropping work. A timeout is a safety ceiling, not a latency benchmark.

For each test, suite, evaluation, lint run or MCP request, set a finite default
deadline supported by its actual runner and an outer deadline that includes
setup and cleanup. Size it from observed workload where possible. If no project
baseline exists, start with an explicit, adjustable fallback such as 30 seconds
for a local case or ordinary MCP request and 5 minutes for a suite or lint run;
long-running evaluations need a declared larger budget. A project may choose
different values. Check that the deadline is truly enforced; a comment or config
field unsupported by the host is not enforcement.

Record monotonic elapsed time, operation/workload identity, deadline, outcome,
and relevant environment/revision with a retained run or trace. Capture timeout,
failure, cancellation and incomplete work separately from a completed slow run.
Use a representative workload, repeated baseline, noise estimate and a justified
user-facing latency target for performance gates; do not add generic timing tests
or turn safety timeouts into arbitrary performance SLOs.

On timeout stop owned local work where supported, report cleanup limitations,
and preserve evidence. A client timeout does not prove an MCP server or remote
provider stopped or rolled back. Mark dispatched side effects as uncertain and
reconcile before retrying. Set bounded retries and total deadlines rather than
allowing a sequence of individually timed operations to run indefinitely.
When the host exposes no request timeout/cancellation, record that gap rather
than claiming the server or request is bounded.

When `.constrain/config.json` supplies `execution.max_jobs` and
`execution.max_timeout_minutes`, the GitHub YAML adapter rejects workflows over
the job budget and ordinary jobs without a literal positive timeout within the
limit. Reusable workflow jobs have no local timeout field and remain a separate
provider-side check. Matrix expansion, transitive reusable workflows, shell
commands, cost and actual runtime are not inferred by this adapter. Capture real
runner traces before claiming a speedup. Use appropriate smaller tests locally
and run required integration checks once before delivery.
