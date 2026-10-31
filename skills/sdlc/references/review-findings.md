# Review requirements and standards independently

Pin the base, reviewed head or dirty diff, workload/spec, and repository standards.
Read surrounding code and reachable callers. Review two independent questions:
does the change fulfill the intended behavior, and does it preserve the project's
documented invariants? Style preferences are not defects.

Use concrete failing inputs or event sequences. For each candidate, record its
location, mechanism, affected requirement, consequence, and smallest correction.
Search for counter-evidence: a validating caller, an impossible state, an already
handled error, a deliberate supported limit. Discard unsupported worries.

Prioritize correctness, security/data loss, supported-load concurrency and
resource behavior, meaningful tests, measured regressions, then unnecessary
complexity. A function's line count alone is not a split criterion. A proven
single-reviewer defect still matters; consensus is neither necessary nor proof.

When authorized independent reviewers are available, give them the same neutral
packet without another reviewer's conclusions. Bound fan-out; preserve actual
model/provider identities. Same-model fresh contexts, different-model panels,
and self-review have different independence. A missing capability stays explicit.

Normalize findings by location and mechanism, retain disagreements, and attempt
to disprove both single and agreed claims before accepting them. Record act,
defer-with-reason, or reject-with-evidence dispositions. Do not inflate findings
to satisfy a count or auto-apply a report-only review.

For full SDLC compliance, the independent reviewer inspects the frozen initial
workload and actual exact-head evidence. Review summaries cannot replace that
comparison or the existing gate. Fixes invalidate affected checks and verdicts.
External comments require the task's actual authorization; a local review does
not itself authorize posting on another person's PR.
