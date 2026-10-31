# Prefer discoverable reusable code assets after demonstrated repetition

Status: accepted. Date: 2026-10-30.

The user wants a skill following the skillify/hookify/lintify naming convention
that produces reusable code mechanisms when patterns are reproduced three or
more times, so future agents reuse an answer rather than deriving it again.

Use the root portable `reusify` package. Search suitable existing code/assets
first, and invoke them immediately. Three verified occurrences, or an actual
requested third use after two existing ones, trigger creating/using the smallest
appropriate asset within authorized scope. Preserve actual occurrence evidence
and distinct policies; a numeric/textual match is not semantic equivalence.

Choose a module/library/component for shared maintained behavior, snippets for
editable source forms, templates for parameterized text/source, and real native
generators for mechanical derivation. Use T4, Copier/Jinja, Roslyn, and other
actual compatible engines rather than adding a private generator language.

Keep a project reuse index at the existing convention, or `.tkstack/reuse/catalog.json`.
Record canonical artifacts and interface/invocation guides. The optional helper
only validates/looks up metadata and observes source ranges; it never executes
catalog content or extracts code. This catalog is separate from correction
authority and workflow execution. Source evidence and actual native tests
remain necessary for extraction, compatibility, and incrementality claims.

Native instructions point to the reuse workflow and catalog conditionally.
Packages remain self-contained; missing project catalogs trigger real source
discovery, not a false assertion that no reusable implementation exists.
