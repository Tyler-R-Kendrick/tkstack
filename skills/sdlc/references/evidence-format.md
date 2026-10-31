# Evidence records and helper limits

The helpers use Python's standard library plus Git and a filesystem clone
utility. They coordinate and check records; the harness supplies real agents,
test runners, artifact capture, PR operations, and independent judgment.

## Frozen evidence policy

`freeze` writes `initial-workload.md` and `baseline.json`. It preserves the
original bytes, base SHA, requirement IDs, check kinds, and per-requirement
artifact applicability. A second freeze is idempotent only for the same inputs.
Use `--evidence-plan <JSON>` to give each requirement its own policy; otherwise
`--check-kind` and `--artifact-kind` apply to every requirement. Defaults are
BDD plus contract verification and no universally required visual artifact.

The workload must justify applicability. Add `screenshot`, `har`, `video`, or
another relevant artifact kind to the requirements that need them. Document
non-behavior atoms using `other` with their real deterministic acceptance
check; do not relabel missing behavior/contract checks as inapplicable.

## Checks and contract identity

Each check has a unique ID, requirement IDs, kind, actual command, result, and
exact checked head. The final gate accepts passing current-head records.
Retain raw red/green logs and reports as additional hashed artifacts.

For each applicable requirement and contract, record separate consumer and
real-provider verification. Both checks identify the same `contract_artifact`
and `contract_sha256`; the retained artifact is hashed and maps to that
requirement. Set `real_provider: true` only when actual producer code was
exercised. Schema validation or a mock alone cannot satisfy that role.

## Artifacts and screenshots

Artifacts are retained relative to the manifest directory. Each has `path`,
SHA-256, requirement IDs, `kind`, `revision`, `capture_command`, and nonempty
`environment` metadata. A `before` artifact names the frozen baseline commit;
candidate artifacts name the exact head. External hosting URLs can be retained
as additional metadata, but the gate needs an accessible local artifact for
integrity checks. Sanitize sensitive HAR and recording content before hashing.

Each required screenshot pair uses `side: before` / `side: after` and the same
`comparison_id`. Its `environment` records matching `viewport`, `device_scale`,
`theme`, `state`, and `fixture`. If a requirement intentionally changes one of
those conditions, define a meaningful controlled comparison in the workload
instead of claiming mismatched images are a matched pair. The strict helper
only accepts matched conditions; retain other useful captures as additional
review evidence.

HAR and video are not universally paired: retain the side(s) the workload
requires. A reviewer must inspect whether their contents demonstrate the
behavior. A filename or matching hash cannot establish that meaning.

## Amendments and findings

An authorized amendment is a separate retained file with `id`, `path`, hash,
`authorized_by` provenance, and `reason`. Optional `requirements_added` and
`requirements_superseded` preserve the original matrix while recording the
change. New requirements can have their own `evidence_plan`. Superseded rows
remain in `compliance` with verdict `superseded` and the matching `amendment`
ID. Independent review must explicitly verify amendments. A provenance field
does not manufacture user authorization; verify it against the actual request.

Findings retain ID, affected requirement, status, resolution, current
`verification_head_sha`, and `evidence` references to retained check IDs or
artifact paths. Only `resolved` and `rejected-with-evidence` close the gate.
The reviewer rechecks the original failure; an unintegrated mitigation branch
cannot close a finding on the candidate.

## Independent approval and merge snapshot

Every applicable initial/amended requirement needs one compliance row citing
its actual checks and applicable artifacts. The reviewer is a real independent
agent/person, not the implementer or a fabricated identifier. Bind approval to
workload SHA, head SHA, and `review-digest` of the inspected payload. A changed
artifact, finding, amendment, or compliance claim changes that digest even if
the Git head stays the same. The digest excludes the approval and PR fields to
avoid self-reference and allow live PR state to refresh.

`gate --merge` additionally requires a current-head PR snapshot asserting green
checks, addressed comments, current approvals, merged dependencies, and
mergeability. Each comment has an accountable disposition and resolution.
Collect that snapshot from the host immediately before the exact-head merge;
the offline helper cannot prove GitHub's state or its freshness by itself.

## Leases and task results

The scheduler atomically claims a ready node, pinning its base and dependency
heads. A completed node supplies JSON proof bound to task ID, initial workload,
actual task-branch head, requirements, checks, and those input heads. Retained
proof hashes are checked before reuse; moved dependency branches block stale
dispatch. Owner `retry` releases an obsolete result or lease before rework.
The lease also pins a transitive PR parent when it differs from the direct
inputs. Completion rejects moved input heads and commits outside task ownership.
Readiness checks the complete accepted dependency chain, including pinned proof
hashes. Reaccepting an ancestor invalidates its descendants even at the same
head when its proof changes. A no-ready response lists stale completed tasks;
their owners use `retry`, refresh their inputs and evidence, and complete them
again. Running descendants cannot finish against invalidated input proof.
New mitigation nodes can extend the graph; an active/completed task definition
cannot silently change underneath its existing lease.

The result records the coordinator's acceptance decision. It is not a shortcut
around running checks or performing independent review. A host must not infer
truth from a synthetic fixture or a template whose status is still pending.
