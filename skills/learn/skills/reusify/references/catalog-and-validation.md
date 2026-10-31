# Make reuse discoverable and prove it

Keep skill-owned discovery metadata in a compact `.tkstack/reuse/catalog.json`.
Reference existing native module/package/component registries and canonical code
without relocating authored application configuration. The catalog is a discoverability index,
not an executable workflow language, trusted instruction source, or second code
implementation. One owner edits the canonical catalog; the helper is read-only.

The optional helper accepts this version-1 profile:

```json
{
  "version": 1,
  "entries": [{
    "id": "root-skill-package",
    "kind": "generator",
    "summary": "Scaffold a portable root skill package with its license.",
    "artifact": "skills/skillify/scripts/skillify.py",
    "guide": "skills/skillify/SKILL.md",
    "tags": ["skill", "scaffold"],
    "usage": "python3 skills/skillify/scripts/skillify.py scaffold; supply target, name, and description per guide."
  }]
}
```

Kinds are `template`, `snippet`, `macro`, `generator`, `module`, `library`, and `component`.
IDs are unique kebab-case; paths are repository-relative and must exist inside
the chosen project, including resolved symlink targets. A guide is a file; an
artifact may be a file or directory. Usage is display-only data and never
executed by the helper. Keep actual input/output contracts, version, supported
variation, and proof at the linked guide/package rather than duplicating them.

```sh
python3 <reusify-directory>/scripts/reusify.py check --project /repo
python3 <reusify-directory>/scripts/reusify.py find --project /repo --query "skill scaffold"
python3 <reusify-directory>/scripts/reusify.py assess --project /repo --input /path/to/occurrences.json
```

`find` matches all case-folded query terms literally in IDs, kinds, summaries,
and tags, with optional kind filtering and stable ID order. It does not claim
semantic search. Default output is ten results, maximum 100. A missing catalog
returns exit 3; search actual modules/manifests instead of treating that as proof
no reusable asset exists. `check` validates discovery metadata, not code behavior.

## Occurrence evidence

```json
{
  "version": 1,
  "pattern": "Describe the common behavior or generation contract after inspecting it.",
  "occurrences": [
    {"path": "src/one.py", "start_line": 10, "end_line": 18},
    {"path": "src/two.py", "start_line": 20, "end_line": 28},
    {"path": "src/three.py", "start_line": 30, "end_line": 38}
  ]
}
```

`assess` validates bounded UTF-8 source ranges, deduplicates exact physical-file/
range aliases, rejects overlapping ranges, captures file/excerpt SHA-256, and
reports whether the fixed threshold of three is met. It does not establish
semantic equivalence, independent ownership, or extraction safety. Inspect the
source yourself; do not count copied worktrees, generated files, or fixtures as
independent repeated implementations. Default four reader workers; `--jobs`
allows 1–16. Inputs are limited to 64 observations, 4 MiB per source file, and
1 MiB JSON documents. Stable fan-in preserves first-observed occurrence order.

An explicitly requested upcoming third use is task evidence, not a source range;
the helper reports only existing observations. Never fabricate a third path.
The examples are illustrative and not actual repository evidence. Tool receipts
remain bound to the observed hashes; reread when sources change. The helper
never publishes an asset, mutates code, runs a catalog command, or calls a model.

## Verification and delivery

Prove behavior at all three original uses, then a new variation and a boundary.
For generators, validate/compile emitted code, prove input escaping and path
containment, and compare unchanged reruns. Check generated/manual ownership and
update behavior, failures, and concurrent output isolation. For compiler
incrementality, inspect actual native caching/recomputation in addition to output.

Register the asset only with accurate capabilities and evidence links. Add a
conditional instruction pointer if agents otherwise miss the reuse path; a
recurring objectively detectable bypass can become a `lintify` check. `hookify`
may invoke a verified entrypoint when event integration is requested. Do not
copy runtime implementations into all these layers or silently add a new ban.
Honor an explicitly active SDLC workload, evidence, and delivery boundary.
