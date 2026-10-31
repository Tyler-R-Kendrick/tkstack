# 0009: Scoped tkstack roots and temporary-session consolidation

Status: accepted, 2026-10-30.

The user wants harness-like global, user, and workspace `.tkstack` roots,
gitignored temporary `sessions/<session>/` directories, and Learn review that
abstracts session experience into reusable artifacts through the ___ify skills.

Define POSIX defaults `/etc/.tkstack`, `~/.tkstack`, and
`<workspace>/.tkstack`, with explicit root environment overrides. Writes select
one scope without fallback. Curated rules read workspace > user > global; a
nearer same-ID record shadows broader ones. An installed shared-store alias
remains supported. Location computation and inspection stay read-only.

Named sessions isolate temporary work, retain their own ignore boundary, and
route session-local namespaces through TKSTACK_SESSION_ID. Shared caches,
canonical locks/leases, and durable steering stay outside sessions. Codify's
execution image uses the shared session temporary-directory primitive. Existing
run/evidence trees remain intact for compatibility; no broad migration/deletion
is implied by discovery.

Learn collects bounded/hash-bound snapshots, the agent explicitly abstracts
observations into scoped principles, and deterministic routing maps those
findings to learn/instructify/reusify/skillify/codify/flowify/lintify/hookify.
Plans preserve canonical targets and actual dependencies. Invoked consolidation
executes authorized artifact work through those skills; automatic feedback
capture stays narrow and reports/audits remain read-only.

Saved evidence, decisions, and promotion receipts live in ignored
`learnings/reviews/`, outside temporary sessions. Authored reusable artifacts
keep their requested/native source paths. This preserves useful learning after
scratch expires without distributing private histories. Sessions are closed
rather than automatically deleted; cleanup must preserve needed evidence and
pending findings and respect active writers.

No keyword classifier pretends to perform abstract thinking. No background
history harvester, automatic TTL/deletion, private executable workflow DSL,
unrequested scope expansion, arbitrary session-command execution, or new
provider/model routing is introduced.
