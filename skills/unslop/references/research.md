# Research and design choices

Reviewed 2026-10-29 (America/Chicago). These are sources of ideas, not additional
installed packages. This skill and its catalog are independently written; no
upstream snapshot was edited. Stable IDs in `catalog/seeds.json` carry the
following `origin` keys so provenance survives catalog evolution.

| Origin | Primary source reviewed | Incorporated | Limits |
| --- | --- | --- | --- |
| user-seeded | User's request to create this skill | Decorative eyebrows, badge spam, obvious-code comments, meaningless tests | Explicit preferences; their boundaries still depend on purpose |
| pstack | [poteto/plugins unslop at 74dd229](https://github.com/poteto/plugins/blob/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/pstack/skills/unslop/SKILL.md) | Inflated prose, rhetorical templates, excess formatting | Did not copy blanket punctuation or rhetorical-device bans |
| deslop | [Cursor Team Kit at 74dd229](https://github.com/poteto/plugins/tree/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/cursor-team-kit/skills/deslop) | Unnecessary comments, defensive noise, type escapes, local style | Preserve real boundary validation and meaningful rationale |
| impeccable | [Impeccable craft floor at 02523ae](https://github.com/pbakaus/impeccable/blob/02523aec3e4c4580102d996d1b6a71fbe062e03f/.agents/skills/impeccable/reference/craft-floor.md) | Inspect actual renders/states; avoid ornamental structure and pseudo-data | Does not impose one visual house style |
| humanizer | [blader/humanizer at 0ef9fe5](https://github.com/blader/humanizer/blob/0ef9fe5bc3572734fd3ae6c448fe00a30cd5dcf0/SKILL.md) | Preserve supported facts and voice; diagnose clusters; recheck meaning | No fake personal experience or authorship-detection claim |
| slopkit | [ehmo/slopkit at b33718b](https://github.com/ehmo/slopkit/tree/b33718bb9283c11b09567dc714f92d90ffb7bd16/skills) (`slopbeth`, `slopgent`) | Distinguish artifact prose from agent reports; truth before brevity; retain decision-relevant caveats | Concision must not remove important uncertainty |
| hallmark | [Nutlope/hallmark at 4f6a46c](https://github.com/Nutlope/hallmark/blob/4f6a46c6dc325d40ab268c93e25c7b96676ebccd/skills/hallmark/SKILL.md) | Separate floor/reflex/finish, avoid decorative labels and invented credibility | Reject arbitrary universal font/color/word-count rules; no automatic redesign |
| frontcraft | [northcrafto/frontcraft at 642af11](https://github.com/northcrafto/frontcraft/blob/642af11cbb89a43aefd265d7c6600dd8b3e047e7/references/anti-slop.md) | Brief before defaults; meaningful badges; task-appropriate functioning controls | Neither dark/neon nor cream/serif nor image-led is universally right |
| matt-tdd | [Matt Pocock tests guidance at a496f55](https://github.com/mattpocock/skills/blob/a496f5513d4a4cf889bc48e189e579f4b0bdf6aa/skills/engineering/tdd/tests.md) | Public behavior, independent expectations, avoid implementation-coupled tests | Small tests, mocks, and snapshots can be meaningful with the right oracle |
| synthesis | This package's media-specific criteria | Brief mismatch, anatomy/geometry, text, materials, identity, temporal and audio artifacts | Must inspect real media; these are craft criteria, not proven generation detectors |

The consequential shared lesson is contextual judgment backed by actual
artifact evidence. A denylist that removes every card, comment, badge, or
gradient would introduce new failures. The catalog therefore includes a
failure example and a legitimate counterexample for every seeded pattern.

Keyword lint can locate candidates but cannot establish purpose, correctness,
visual coherence, or AI authorship. Hash checks establish which files were
reviewed, not whether a reviewer was truthful. Automated regression fixtures
test this package's persistence and grading mechanics; they are not a measured
improvement in creative quality or a benchmark of the cited skills.
