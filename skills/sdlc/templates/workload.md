# Workload: <stable workload ID and outcome>

Create this before implementation. Preserve the original as an immutable
artifact and record its hash in the task graph, branch handoffs, evidence index,
and final compliance review. Keep progress elsewhere. Record later authorized
scope changes under amendments without rewriting the initial requirements.

## Identity and original scope

- Workload ID: `<workload-id>`
- User request/source: `<message, issue, or document reference; preserve the requested outcome>`
- Repository: `<forge and owner/repository>`
- Starting commit: `<full immutable SHA>`
- Initial workload artifact: `<path or durable URL>`
- Baseline manifest: `<external manifest that records this artifact's SHA-256 after freezing>`
- Target consumer/user: `<who benefits and how>`
- Completion outcome: `<observable behavior that makes the requested work complete>`
- Exclusions: `<specific behavior outside the current authorized scope>`
- Existing constraints: `<compatibility, delivery, runtime, or policy constraints>`

The hash belongs in the external baseline manifest. Inserting it into the
already frozen workload would change the bytes being identified. The task
graph and evidence manifest reference that same `workload_sha256`.

## Requirements

Use stable IDs. Each requirement names observable behavior and its provenance.
Separate facts required by the user from implementation choices.

| ID | Source | Required behavior | Applicability and limits | Acceptance scenarios | Required evidence |
| --- | --- | --- | --- | --- | --- |
| R-001 | `<user/issue reference>` | `<one observable outcome>` | `<contexts and constraints>` | S-001 | `<artifact/report types>` |

## BDD scenarios

### S-001: <one behavior variation>

- Requirements: `R-001`
- Public seam: `<interface or component at which behavior is observed>`
- Contract obligations: `C-001`, or `<not applicable and why>`
- Given: `<state, fixtures, actor, permissions, and dependency versions>`
- When: `<one action or event>`
- Then: `<observable result, including relevant side effects>`
- Negative/boundary cases: `<invalid input, denial, empty data, retry, race, or limits as relevant>`
- Deterministic acceptance check: `<test IDs/command and independently derived expected values>`
- Red reproduction: `<how to observe the intended failure before implementation>`
- Green proof: `<expected successful observation>`

Repeat with a new scenario ID for each independently meaningful variation.

## Contracts and compatibility

### C-001: <public boundary>

- Contract owner: `<task/role responsible for the versioned contract artifact>`
- Producer: `<real implementation and immutable version/artifact digest>`
- Consumers: `<implementations and immutable versions/artifact digests>`
- Interaction examples/artifact: `<path or immutable reference>`
- Request/event shape: `<schema and relevant examples>`
- Response/acknowledgment shape: `<schema and relevant examples>`
- Semantics: `<errors, side effects, ordering, retries, idempotency, or version negotiation>`
- Consumer verification: `<behavior checks against the contract examples>`
- Real-provider verification: `<checks running those examples against the actual producer>`
- Supported compatibility matrix: `<old/new producer and consumer combinations required to work>`
- Migration/rollback constraints: `<additive change, compatibility window, deployment ordering, and reversal>`
- Stub use: `<where a stub assists development and where actual producer proof is required>`

## Atomic deliverables and graph boundaries

Each deliverable is the smallest independently verifiable behavior or contract
change. Split a node when its acceptance conditions, owners, or dependency
frontiers can move independently. Preserve enough context for a meaningful
green commit; a file, method, or arbitrary line count is not an outcome.

| Task ID | Granular deliverable | Requirement/scenario IDs | Contract artifact/version | Prerequisites | Owned paths/seams | Acceptance condition |
| --- | --- | --- | --- | --- | --- | --- |
| T-001 | `<one verifiable outcome>` | `R-001 / S-001` | `C-001 @ <version>` | `<task IDs or none>` | `<exclusive write scope>` | `<specific green observation>` |

- Task graph artifact: `<path; every edge represents a real dependency>`
- Independent ready frontier: `<nodes able to run concurrently after prerequisites are met>`
- Shared-contract or shared-file owner: `<one owner or prerequisite node>`
- Branch/worktree assignment: `<task branch and isolated sparse worktree per graph branch>`
- Cache policy: `<shared immutable content-addressed cache; private mutable outputs>`
- Copy-on-write capability: `<verified filesystem capability or explicit fallback status>`
- Commit/PR stack: `<incremental green commits and parent/base relationships>`
- Review allocation: `<implementation owner, independent adversarial reviewers, mitigation owners>`

## Evidence plan

Choose the evidence needed by each requirement before changing the baseline.
Use BDD and contract checks rather than a new full-system E2E acceptance suite.

Decide applicability per requirement. A non-UI change need not produce a HAR,
screenshot, or video. Where visual comparison is applicable, require a matched
before/after screenshot pair; a network trace or interaction recording needs
the side(s) necessary to prove the stated behavior, rather than a universal
pair requirement.

| Requirement ID | Visual comparison | Network/HAR | Motion/interaction recording | Applicability rationale |
| --- | --- | --- | --- | --- |
| R-001 | `<required / not-applicable>` | `<required / not-applicable>` | `<required / not-applicable>` | `<why each selected artifact proves this requirement>` |

| Evidence ID | Requirement/scenario/contract IDs | Observation/artifact | Baseline state/ref | Candidate state/ref | Capture/check procedure | Durable location |
| --- | --- | --- | --- | --- | --- | --- |
| E-001 | `R-001 / S-001 / C-001` | `<red and green reports; real-provider verification>` | `<immutable ref and fixture>` | `<head and dependency refs>` | `<command/procedure>` | `<artifact path or URL>` |
| E-002 | `<applicable IDs>` | `<before/after screenshots, HAR, video, trace, or reason not applicable>` | `<viewport/theme/state/ref>` | `<matching conditions/ref>` | `<capture procedure>` | `<artifact path or URL>` |

Every produced artifact records its actual code revision, dependency versions,
environment, fixture, result, and content hash. Plan sanitization for HAR files
and recordings. Missing browser access or an expired artifact is a concrete
evidence gap, not an automatic not-applicable result.

The final evidence manifest binds `workload_sha256` and the exact `head_sha` to
hashed artifacts, requirement IDs, capture side/revision, and BDD/contract check
records containing their commands, results, and revisions. Review dispositions
reference those actual artifact and check IDs. Record the independent reviewer's
identity, review scope, and findings ledger alongside the compliance report.

## Delivery and merge gate

- Required inner-loop checks: `<targeted behavior and contract commands>`
- Required outer-loop checks: `<affected compatibility matrix, integration, and required CI>`
- Adversarial review lenses: `<correctness, contract drift, regressions, concurrency, security, or maintainability as relevant>`
- Findings/mitigation ledger: `<stable IDs, reproduction, owner, resolution, and independent recheck>`
- Final compliance reviewer: `<independent of implementation>`
- Compliance input: `<this immutable initial workload, hash, amendments, branch requirement subset, latest-head evidence index>`
- Compliance output: `<one disposition per applicable requirement with direct evidence and rationale>`
- PR stack: `<parents, base branches, merge order, and retarget/restack procedure>`
- PR babysitting: `<checks, bot/human review threads, actionable comments, and mergeability monitored through merge>`
- Merge policy: `<squash each incremental PR into the protected target, lowest dependency first; refresh descendants after each parent merge>`
- Completion proof: `<merged PR URLs and squash SHAs, green final checks, resolved comment/finding ledger, and workload compliance report>`

## Authorized amendments

Keep this separate from the immutable initial artifact. Name the authorizing
request and explain its effect on requirements, scenarios, graph branches,
contracts, evidence, and existing PRs.

| Amendment ID | Authorizing source | Change and rationale | Affected stable IDs | Required revalidation |
| --- | --- | --- | --- | --- |
| A-001 | `<new user request or explicit scope decision>` | `<what changes>` | `<R/S/C/T/E IDs>` | `<checks and artifacts invalidated>` |

## Final requirement-to-evidence review

Populate in a separate review artifact, preserving this template's initial
requirements unchanged. Each branch compares its original assigned workload
with current evidence; the integration reviewer also checks cross-branch
requirements and the complete workload.

| Requirement ID | Initial expectation and amendments | Current head/dependency refs | Inspected evidence IDs | Disposition | Reviewer rationale and mitigation |
| --- | --- | --- | --- | --- | --- |
| R-001 | `<original behavior plus authorized changes>` | `<immutable refs>` | `<actual artifacts inspected>` | `<pass / fail / blocked / workload-supported not-applicable>` | `<observations and remaining work>` |

Completion requires every applicable requirement to pass, every blocking
finding and review comment to be addressed, required checks to remain green,
and the intended stack to be confirmed merged. A checklist alone does not prove
the artifacts demonstrate compliance.
