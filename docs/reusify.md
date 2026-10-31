# Reusify

Use `/reusify <pattern>` or `$reusify` to turn repeated code into a canonical
reusable asset. The [portable skill](../skills/reusify/SKILL.md) covers templates,
snippets, native code generators, shared modules/libraries, and UI components.
Its name follows skillify/hookify/lintify and names the desired action: reuse.
Subcommands are optional; omitting one keeps the targeted pattern workflow.

Use `/reusify init [scope]` to bootstrap deterministic code production from an
existing codebase. It discovers existing assets and real repeated patterns,
extracts suitable snippets/templates/macros/codegen/shared code, migrates
applicable uses, registers actual invocations, and checks native behavior and
unchanged-input repeatability. It must deliver usable assets rather than stop
at an inventory. Explicit preview/audit is read-only. Scope, kinds, limits, and
concurrency parameters are detailed in the [init reference](../skills/reusify/references/init.md).

These are agent skill invocations. The Python catalog/evidence helper below
keeps its read-only `find`/`check`/`assess` interface; it has no shell `init`
command and does not perform semantic extraction itself. Initialization is
not automatically run when the skill is installed.

Before reproducing a pattern, look up existing code, dependencies, templates,
snippets, and generators. Use a suitable asset immediately. At three verified
occurrences, or when the requested new use would be the third, create/use the
smallest fitting asset within scope. Record actual evidence; never pretend a
proposed third use is already implemented. An audit-only request stays read-only.

The threshold triggers action, not blind abstraction. Shared runtime code makes
fixes propagate. Snippets create editable copies. Templates/generators derive
source from explicit parameters. Similar-looking code with incompatible policy
needs a justified smaller shared invariant or separate implementations, not an
options-heavy universal wrapper.

## Lookup before inference

The project's [reuse catalog](../.tkstack/reuse/catalog.json) indexes existing skill,
lint, workflow, and instruction generators plus the new Copier example. These
are actual existing entrypoints, not invented implementations. Reusify itself
was created using skillify's existing scaffolder.

```sh
python3 skills/reusify/scripts/reusify.py check --project .
python3 skills/reusify/scripts/reusify.py find --project . --query "skill scaffold"
python3 skills/reusify/scripts/reusify.py find --project . --query "lint rule"
python3 skills/reusify/scripts/reusify.py assess --project . --input /path/to/occurrences.json
```

The helper is read-only. It performs bounded literal catalog lookup, validates
local references, and counts bounded observed source ranges with hashes.
Physical aliases do not inflate the threshold; overlapping ranges are rejected.
It does not discover semantic clones, run usage strings, mutate code, or prove
that three snippets are equivalent. A missing catalog returns exit 3 and routes
back to real source/dependency discovery.

Each registered asset links its current interface guide, invocation, inputs,
outputs, version, tests, and limits. Metadata is a route to actual code, not a
new executable DSL or a substitute for checking compatibility. Standalone skill
copies do not require this dotfiles catalog or any sibling package.

## Native formats and evidence

Conditional references cover T4 host distinctions and `.tt`/`.ttinclude` usage,
Roslyn `IIncrementalGenerator` pipelines and equality/cancellation semantics,
native editor snippets, shared runtime components, and native macro expansion.
Use their actual language/build contracts; the catalog supports `macro` entries
and filtered discovery. Keep source generation additive where the native API
requires it; source rewriting is a different tool.

The working Copier 9.7.1 example uses native YAML/Jinja, typed validated inputs,
and a hashed dependency lock resolved/tested on CPython 3.12/Linux.
Its reusable verifier runs the actual CLI, compiles/consumes generated Python,
checks quotes/non-BMP Unicode/code-shaped literals, rejects invalid input, and
compares unchanged generated module bytes. Outputs are isolated and work is
bounded. The initial native run caught a Unicode literal bug; the retained
before/after receipts are under `.tkstack/evidence/reusify/`.

```sh
python3 skills/reusify/examples/copier/verify.py --copier /path/to/copier
```

The local validation environment is ignored at
`.tkstack/evidence/reusify/copier-venv`. No T4, Roslyn compiler, or editor-native
execution is claimed. Those adapters require their actual compatible hosts.
Catalog/occurrence helper tests and structural package checks do not establish
model compliance, semantic clone detection, or measured inference reduction.

Existing helpers and upstream snapshots remain owned by their current packages.
Creating this skill does not publish a package, migrate unrelated code, install
an editor snippet, enable a lint/hook, or start the full SDLC workflow.
