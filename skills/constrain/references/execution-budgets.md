# CI and execution

Choose fixed workload, cache conditions and meaningful work first. Budget job
count, deadlines, worker capacity, network access, and costly optional tests;
separate performance measurement from correctness checks. Do not shorten a run
by dropping work. A timeout is a safety ceiling, not a latency benchmark.

When `.constrain/config.json` supplies `execution.max_jobs` and
`execution.max_timeout_minutes`, the GitHub YAML adapter rejects workflows over
the job budget and ordinary jobs without a literal positive timeout within the
limit. Reusable workflow jobs have no local timeout field and remain a separate
provider-side check. Matrix expansion, transitive reusable workflows, shell
commands, cost and actual runtime are not inferred by this adapter. Capture real
runner traces before claiming a speedup. Use appropriate smaller tests locally
and run required integration checks once before delivery.
