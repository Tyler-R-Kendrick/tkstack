# Saved grading reports

For ordinary reviews, concise findings with concrete evidence suffice. For an
evaluation run or retained before/after comparison, obtain a scoped snapshot:

```sh
python3 <skill-directory>/scripts/unslop.py show --domain code --domain tests
```

Copy its `sha256` into `catalog_sha256`. The input report has:

```json
{
  "brief": "Implement the specified input validation without speculative layers.",
  "domains": ["code", "tests"],
  "catalog_sha256": "<current scoped catalog hash>",
  "artifacts": [{
    "id": "implementation",
    "path": "../src/validate.py",
    "sha256": "<sha256 of actual bytes>",
    "domains": ["code"],
    "inspections": ["source"]
  }],
  "judgments": [{
    "pattern": "narration-comments",
    "status": "finding",
    "reason": "Comments repeat every simple assignment without rationale.",
    "evidence": [{"artifact": "implementation", "location": "lines 14-28",
      "observation": "Five comments restate the following variable assignments."}],
    "fix": "Remove narration and keep the comment explaining the input constraint."
  }]
}
```

This abbreviated example is intentionally incomplete. Add real test artifacts
and one row for **every** pattern in the selected snapshot. Include repository
and task IDs when those scopes apply. Paths resolve relative to the report
file, not the installed package. Artifacts are read-only and hashed in place.

Judgment statuses are `clear`, `finding`, `exception`, `not-applicable`, and
`unreviewed`. Each has a reason; every reviewed row needs an artifact citation
with location and observed evidence. An exception explains how the brief or
meaningful use justifies a reflex; floor failures cannot be waived as taste.
Not-applicable means the inspected artifact has no relevant feature, not that
the reviewer skipped it. An unreviewed row remains incomplete.

Inspections: source for writing/code/tests; actual render for web; image for
images; video for video; audio for audio. A video with sound requires both
domains to assess both. Include source and rendered artifacts separately if
needed. These declarations are **reviewer attestations**, not tool receipts.
Every artifact needs its declared domain's inspection; viewing one image cannot
cover an uninspected second image. The helper cannot verify that a render was
opened or an audio track listened to.
Attach actual screenshots, recordings, transcripts, and test logs to the
review/workload evidence when they substantiate the finding.

```sh
python3 <skill-directory>/scripts/unslop.py grade --input report.json
```

Exit 0: pass; 2: incomplete or needs work; 1: invalid or stale report.
The score is `100 × (reviewed weight − finding weight) / reviewed weight`;
not-applicable rows are excluded. Missing pattern rows, unreviewed rows, or a
selected domain without its required inspection make the score null. Any
finding requires work; floor blockers are reported independently of the score.
All-not-applicable reviews have no numeric score.

Changing an artifact or applicable catalog invalidates the report and requires
fresh inspection. Preserve old reports as historical evidence rather than
updating their hashes to imply that a new artifact was reviewed. Scores are
editorial summaries of supplied judgments, not probabilities of AI authorship
and not proof of correctness. Fixed-rubric comparisons used by `hill-climb`
must restart if a new user correction changes the rubric mid-run.
