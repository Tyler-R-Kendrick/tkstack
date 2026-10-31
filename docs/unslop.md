# Anti-slop review and learning

[`skills/unslop`](../skills/unslop/SKILL.md) is the canonical personal package.
Use `/unslop <artifact>` to inspect and correct it, `/unslop grade <artifact>`
for read-only grading, or `$unslop` in Codex. User-identified slop also triggers
capture and application during an ongoing task. Restart the harness session
after installation to discover the new skill.

The catalog starts with 32 patterns across writing, code, tests, websites,
images, video, and audio. The user's four seeds are decorative eyebrow labels,
badge spam, comments narrating obvious code, and tests with no meaningful
oracle. Other seeds include empty rhetorical templates, fake credibility,
speculative code layers, mocks pretending to be contracts, template-driven
interfaces, garbled visual text, and unintentional geometry/continuity defects.
Every pattern includes a purpose-based exception and a counterexample.

[Research notes](../skills/unslop/references/research.md) document Pstack,
Cursor Team Kit, Impeccable, Humanizer, Slopkit, Hallmark, Frontcraft, and Matt
Pocock. These informed an independently written catalog; they were not installed
as new bundles. Source snapshots remain unchanged. No universal aesthetic,
punctuation ban, or AI-authorship detector is asserted.

The new bare `unslop` resolves to the personal package in Codex, Claude, and
Cursor. The original Pstack writing skill is retained as `pstack-unslop`.
Only its declaration/view is adapted; other Pstack calls to `unslop` intentionally
reach the personal skill. The installer migrates an old link only when it
resolves to this checkout's exact former upstream source. Foreign paths remain
protected, and the pinned original stays byte-identical.

## Shared correction history

The package uses the same `.tkstack/steering/events.jsonl` and writer lock as `learn`.
User corrections/preference records are deduplicated by exact quote plus
message provenance; later recurrence is additional evidence. `slop-pattern`
events retain abstract criteria and all earlier evidence IDs. Active confirmed
criteria enter the generated catalog; candidate interpretations and retired
preferences stay out of grading. A reversal appends history rather than
deleting it. The actual initial request is labeled `preference`.

```sh
python3 skills/unslop/scripts/unslop.py show --domain code --domain tests
python3 skills/unslop/scripts/unslop.py record --input /path/to/correction.json
python3 skills/unslop/scripts/unslop.py render
python3 skills/unslop/scripts/unslop.py check
python3 skills/learn/scripts/learn.py check
```

Both helpers resolve an explicit store, environment override, project/home
steering link, or this checkout's canonical store. Standalone marketplace copies
fall back to the working project, never their plugin cache. See the
[record contract](../skills/unslop/references/records.md).

Native Codex/Claude instruction blocks and the Cursor steering rule route output
grading and new user-identified patterns through unslop. The full dotfiles setup
shares the same canonical store across harnesses. A plain marketplace copy
has the package and seeds but requires its own instruction pointer if automatic
startup routing is desired. New corrections update data, not the skill prompt;
procedural prompt revisions use `learn improve` and its normal validation gate.

## Evidence and grading

Reviewers inspect real artifacts and classify each applicable criterion.
Saved reports pin catalog and file hashes, cite observed locations, and cover
every applicable pattern. Missing inspection or coverage yields an incomplete
grade. Truth, required functionality, accessibility, and verification honesty
cannot be offset by a high aggregate score. Legitimate status badges, WHY
comments, small meaningful tests, and requested visual styles remain valid.

The offline helper checks report structure, coverage, hashes and supplied
judgments. It cannot verify that someone actually opened an image or watched
a video, determine the semantic truth of a claim, or establish AI authorship.
Source-only review never proves rendered quality. See the
[grading format](../skills/unslop/references/grading.md). A catalog change
invalidates an old scoped report; a fixed-rubric hill-climb must rebaseline.

Regression tests cover persistence, shared-ledger compatibility, recurrence,
candidate/scope/retirement boundaries, standalone copies, stale proof, missing
inspection, and nonwaivable floors. Synthetic review fixtures test the report
contract; they are not a creative-quality benchmark or a model evolution trial.
