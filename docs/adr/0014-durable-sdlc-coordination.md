# Durable local SDLC coordination and requirement revisions

Status: accepted for the local dotfiles workflow.

The SDLC JSON scheduler rewrote one state file under a directory lock, could
leave a stale lock after process death, and did not encode the return from a
development discovery to requirements/architecture planning. Graph state must
survive harness restarts and session cleanup while supporting bounded workers.

Use Python's embedded SQLite with WAL, FULL synchronous durability, and short
version-checked write transactions. Keep the database at the explicitly selected
scoped `.tkstack/sdlc/task-graph.sqlite3`, covered by the existing ignore policy.
Store per-task lease records and append-only revision/event history. Reuse the
existing Git/proof transition validator, validate static graphs at registration,
and batch branch refs outside writer locks. Retain JSON compatibility for old
runs rather than silently migrate active owners.

A local SQLite server would add a service lifecycle without improving this
single-machine ownership boundary. A network/coordinator service is a future
choice only when workers genuinely need multiple machines; copying SQLite files
or using a network filesystem is not that service. A relational server is not
needed for the present workload. A locked JSON file remains insufficient for
transactional revision history and crash-safe ownership without new machinery.

Lease tokens fence stale publications, but expiration cannot terminate a worker.
Never automatically reassign its writable worktree. Owners quiesce; coordinators
recover expired/blocked records with retained evidence of stopped writes.

Unexpected findings create explicit issues and pause their affected downstream
closure. The coordinator appends authorized requirement dispositions and ADRs,
quiesces affected live workers, replans, and invalidates affected evidence.
Preserve original workload bytes, prior results, and amendment history. Truly
unchanged independent work can carry its old claimed workload hash through an
explicit unchanged disposition. Final independent review reconciles original
requirements, amendments, architecture decisions, and current evidence.

Strict Markdown/OpenAI command signatures dispatch the compiled coordinator
artifact. Mechanical checks execute without inference; choosing a meaningful
requirement revision/ADR still uses the coordinator's actual judgment and
authority. Local records cannot authenticate authorization or remote PR state.

Validation covers real concurrent process claims, capacity, SQLite crash rollback,
restart persistence, stale tokens, quiescence, revision invalidation, unaffected
proof carry-forward, Git ignore behavior, retained ADRs, and typed invocation.
Synthetic task proofs test coordination contracts, not production BDD/provider
checks or an actual remote PR delivery.
