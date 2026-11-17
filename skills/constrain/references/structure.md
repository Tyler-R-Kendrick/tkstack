# Repository structure and documentation

Assign each maintained fact and artifact one owning location. Extend the
existing owner before adding another file, directory, README, knowledge store,
or duplicated instructions. Preserve required interfaces and accessibility;
raw file count or a byte ceiling does not prove information quality.

`layout.budgets` enforces configured file/byte/depth limits over selected Git
snapshot paths. `documents.include`/`exclude` enables exact-byte duplicate
checks over Markdown files; it does not detect paraphrases, duplicated claims,
or whether a document remains useful. The documentation checker separately
owns link validity and explicit source/doc freshness. Review actual content and
consumer paths before consolidating. An owned-tree budget prevents moving bloat
to an unmeasured directory; pinned vendor snapshots remain immutable and are
excluded from owned budget counts.
