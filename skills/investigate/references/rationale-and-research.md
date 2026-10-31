# Rationale and primary-source research

Current code establishes behavior; it rarely establishes the author's intent.
Anchor historical questions in exact symbols, file versions, relevant commits,
and the date of the decision. Read the associated PR, issue, ADR, release note,
or discussion when accessible. Quote the original rationale where its wording
matters. Distinguish the design as proposed from the implementation that landed.

For external APIs or tools, resolve the maintainer, canonical repository, exact
package, version, and primary documentation before choosing an implementation.
Prefer the source owner over search snippets. Verify installation and runtime
behavior separately from a README claim.

Search independent relevant sources concurrently within the task's scope.
Do not query every connected private system automatically. Record which sources
were available, searched without a result, or inaccessible. A missing archived
thread does not prove the decision lacked a reason.

Build a compact claim/evidence table when the conclusion is contested:

| Claim | Direct evidence | Contrary evidence | Remaining uncertainty |
| --- | --- | --- | --- |
| The behavior changed in this revision | Exact diff and reproducing result | An earlier reproduction may disagree | Supported versions not exercised |

Try an alternative explanation before settling. Preserve contradictions rather
than smoothing them into a story. Label inference explicitly; do not translate
plausibility, model agreement, or confidence language into historical fact.

Write findings to the requested artifact or the repository's established notes
location. A research request does not authorize posting to chat, an issue tracker,
or a public site. Finish with the answer and its limits, not a search transcript.
