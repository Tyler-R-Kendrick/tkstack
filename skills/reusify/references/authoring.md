# Turn repetition into reuse

Before implementing another instance, search the project's actual packages,
modules, components, scaffolds, snippets, templates, code generators, and reuse
catalog. Search by the capability/invariant, not just a proposed class name.
Inspect a matching asset's real interface, supported inputs, ownership, and
tests. Use it immediately if suitable; reuse does not wait for three copies.

## The third occurrence is an action trigger

Identify three distinct occurrences of the same meaningful pattern. Record
their actual paths/ranges or separately sourced task artifacts, common behavior,
and differences. Generated outputs, fixtures that intentionally repeat examples,
symlink/hardlink aliases, or copied worktrees are not independent implementation
evidence. Several occurrences in one file can count when they are distinct.
Do not invent a third occurrence or treat textual similarity as equivalent intent.

At three verified occurrences, create/use an appropriate reusable asset within
the authorized scope. Do not merely note duplication and write a fourth copy.
When an interface cannot safely be shared, use a template/snippet or a smaller
shared invariant instead. If the cases require incompatible policies or the
change crosses a real scope boundary, retain concrete evidence and the bounded
reason; do not silently generalize or defer the reuse obligation.

When two implementations exist and the requested new use would be the third,
make the reusable asset before producing that copy. Keep the new requirement
distinct from observed source evidence; do not claim a proposed file exists.
Audit/report-only scope remains read-only even when the threshold is met; return
the concrete reuse choice and its evidence without performing an excluded edit.

An explicit request can create an asset with fewer examples. Do not fabricate
usage history to justify that request. A two-occurrence threshold is not imposed
on existing reusable code: existing assets should be used whenever suitable.

## Choose what changes together

| Repeated need | Asset | Update behavior |
| --- | --- | --- |
| Same behavior/invariant at multiple callers | Function, module, library, component | One maintained implementation; migrate callers |
| Small editable syntactic form | Native editor snippet | Expansion creates an independent copy |
| Repeated syntax best expressed by the language's expansion mechanism | Native macro | Canonical expansion under the real compiler/build contract |
| Repeated source from explicit parameters/model | Native text template, T4, Jinja, or project scaffold | Regenerate from canonical inputs/template |
| Compiler-derived declarations or metadata glue | Native generator, such as Roslyn incremental generation | Compiler/build graph derives owned source |
| Existing bulk copies need migration | Existing codemod or bounded migration | Change existing callers with behavior proof |

Select the least machinery that preserves the invariant and legitimate variation.
Do not add a runtime library just to insert syntax, or a compiler plugin when a
shared function would remove the duplication. A generator is useful when source
really must vary; templates are not a substitute for shared business logic.

Write a caller example first. Fix inputs, outputs, errors, ownership, supported
variations, generated/editable boundaries, and update/compatibility policy.
Use deterministic algorithms, schemas, native engines, and configuration for
repeated work. An LLM can help design a new abstraction/template, but future
instances invoke it instead of asking the model to reconstruct the algorithm.

Migrate applicable occurrences in small coherent units and preserve behavior.
Avoid flag-driven universal abstractions, wrappers that hide no useful complexity,
or an options surface larger than the repeated implementation. Shared code must
remain safe under concurrent callers: isolate mutable state, bound resources,
define cancellation, and make output/order stable. Prefer the host's incremental
or parallel execution instead of nested worker pools.

Register the asset where future work will look. Include its purpose, interface,
inputs, outputs, version, invocation/import, tests, limitations, and examples.
Point agent instructions to that canonical source when needed; do not duplicate
the entire implementation into every skill or startup instruction file.

For codebase-wide bootstrap, use the optional [init workflow](init.md); a
targeted request without a subcommand keeps this procedure. Procedures belong
in `skillify`, CLI rules in `lintify`, event guards in `hookify`, executable
orchestration in `flowify`, and instruction pointers in `instructify` when
available. Those sibling packages are optional; avoid duplicating their code
or treating their installation as permission to activate a new policy.
