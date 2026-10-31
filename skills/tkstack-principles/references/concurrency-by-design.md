# Concurrency by design

**Trigger:** designing, implementing, or reviewing any code or executable
workflow. Optimize the design for concurrency and parallel composition from
the outset, including utility code used by concurrent callers.

**Reason:** accidental shared state and sequential orchestration constrain
throughput. Independent work should be able to progress concurrently while
preserving correctness, resource bounds, and reproducible outcomes.

## Design the work and ownership first

1. Define units with explicit inputs, outputs, dependencies, read/write sets,
   and ownership. Model multiple operations as a dependency graph. Make the
   readiness condition executable when building an orchestrator; don't rely
   on an agent to guess which prerequisites are complete.
2. Run ready, independent work concurrently. Prefer batch APIs, bounded async
   I/O, vectorization, worker pools, or processes as appropriate to the workload.
   Account for runtime constraints such as the Python GIL for CPU-bound work.
   Avoid serial awaits over independent I/O and avoid unbounded task fan-out.
3. Eliminate shared mutation before adding locks. Prefer pure functions,
   immutable inputs, per-task buffers, independent output keys, and isolated
   branches/workspaces. Share immutable caches or use cache infrastructure with
   correct atomic publication; never share writable build outputs blindly.
4. Where a single canonical mutable resource is a real invariant, enforce
   ownership with a single-writer queue, transaction, compare-and-swap, lease,
   atomic publication, or appropriate lock. Keep the critical section small;
   independent preparation and reads should stay concurrent where safe.
5. Bound concurrency by actual CPU, memory, disk, database, provider quotas, and
   rate limits. Use backpressure, cancellation, deadlines, and bounded queues.
   Avoid nested pools that multiply demand without a shared capacity budget.
6. Make fan-in stable. Associate results with input/task IDs, preserve required
   output order, use explicit tie-breakers, and define how partial failures
   affect dependents. Completion order must not silently choose a winner or
   change a decision. Await/join owned work; do not leave orphan background tasks.

Parallel execution cannot remove real data dependencies or ordering constraints.
Name the concrete constraint for a serialized stage: dependency, required
side-effect order, canonical writer, resource/rate limit, or measurement
integrity. Serialize the smallest necessary region. Existing serial code or
implementation convenience alone is not a reason to serialize independent work.

## Preserve behavior under overlap and failure

Make retryable effects idempotent where possible, with stable operation IDs
and deduplication at the owning boundary. Don't imply exactly-once behavior
without a mechanism that provides it. Define timeouts, retry limits, and
failure propagation; avoid retry storms. A lock protects only the participants
and scope it actually covers, and atomic rename alone does not prevent lost
updates between competing read-modify-write operations.

Use explicit synchronization and meaningful behavioral tests for relevant
risks: out-of-order completion with stable output, resource-bound enforcement,
duplicate requests, cancellation, conflicting writes, partial failure, or crash
recovery. Prefer barriers/events/controlled schedulers over timing guesses and
sleep-based assertions. Verify public contracts and invariants, not merely
thread/task counts. Measure throughput/latency and contention when claiming an
optimization; concurrency can worsen performance under the wrong resource mix.

## Examples and boundaries

- **Repository inspection:** batch independent file/API reads concurrently;
  process their outcomes in a stable order and inspect failures. A dependent
  edit waits for the facts it needs.
- **Agent task graph:** use independent sparse worktrees and branch ownership,
  with immutable/shared-safe dependency caches. In an active `sdlc` workflow,
  honor its verified COW, leasing, workload, and evidence requirements. This
  principle does not itself grant permission to spawn agents or push changes.
- **Canonical correction ledger:** different workers can prepare observations
  independently, while the existing writer lock serializes append/deduplication
  for the one shared evidence history. Do not remove that lock to increase
  nominal parallelism or perform stale read-modify-write outside its ownership.
- **Benchmarking:** parallelize independent setup, but isolate or serialize
  measurements when concurrent contenders would distort the intended workload.
  Keep measured cache, warmup, and resource conditions explicit.
- **Boundary:** a small pure parser remains a simple synchronous function that
  concurrent callers can safely reuse. Do not add a pool per function or run
  ordered mutations concurrently. Safe composition and bounded throughput are
  the optimization goal; task count is not a success metric.
