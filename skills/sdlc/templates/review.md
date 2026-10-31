# Workload compliance review: <task ID>

Status: pending. This template is not an approval.

## Frozen inputs

- Initial workload path and SHA-256:
- Workload baseline Git SHA:
- Accepted amendment paths and identities, or none:
- Candidate head SHA and intended PR base SHA:
- Dependency task IDs, exact heads, and merged outcomes:
- Evidence manifest path and digest:
- Evidence/compliance payload digest returned by `sdlc.py review-digest`:
- Independent reviewer identity and role:

## Requirement-to-evidence matrix

Inspect the initial workload directly. Include every requirement and accepted
amendment, including negative scenarios, compatibility, and applicable runtime
evidence. Replace placeholders with observations; an empty row is incomplete.

| Requirement ID | BDD outcome / contract obligation | Check IDs and current-head results | Artifact paths, hashes, and before/after revisions | Verdict: pass/fail/blocked | Rationale or concrete gap |
| --- | --- | --- | --- | --- | --- |
| <R-ID> | <Given/When/Then or boundary obligation> | <BDD/consumer/provider check IDs> | <appropriate proof or workload-backed applicability decision> | pending | <what was actually inspected> |

## Adversarial findings and mitigation

| Finding ID | Reviewer and reviewed head | Requirement / failure mechanism | Severity | Mitigation commit or counterevidence | Verification head and result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| <F-ID> | <identity, SHA> | <reproducible claim> | <level> | <commit or reasoned rejection> | <current SHA and proof> | open |

## Evidence freshness

- Artifact hashes and accessibility checked:
- Before/after captures refer to the intended baseline and candidate builds:
- Relevant environment, fixtures, and contract versions identified:
- Changes since capture or review, and the checks/captures rerun:
- Any reused evidence and its explicit mechanical-equivalence argument:
- Missing evidence or blocked checks:

## PR and stack gate

- PR URL, current head, and current base:
- All task dependencies confirmed merged:
- Required current-head checks and approvals:
- Every comment/thread classified, addressed, and resolved where applicable:
- No open blocker or unresolved human change request:
- Old parent/child boundary SHAs saved before squash or restack:
- Intended squash merge method and protection/queue requirements:

## Independent decision

- Requirements complete: **no, pending inspection**
- Verdict: **pending** (`approve`, `changes`, or `blocked` after inspection)
- Workload SHA-256 covered by this verdict:
- Head SHA covered by this verdict:
- Specific evidence behind the verdict:
- Outstanding requirement IDs and blockers:

An approval expires for the affected proof when the candidate, base, contract,
fixture, dependency, or configuration changes. Reconcile the changed evidence
and bind the next verdict to the actual workload/head pair before landing.
