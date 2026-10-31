# Init: extract reusable code-production assets

Invoke `/reusify init [scope]` or `$reusify init [scope]` to bootstrap reuse in
an existing codebase. The subcommand is optional: `/reusify <request>` retains
the targeted [authoring workflow](authoring.md). `init` is an agent skill
workflow, not an undocumented `scripts/reusify.py init` command.

Deliver usable snippets, templates, macros, native codegen, or shared code,
with discoverable, tested invocations. Inventory alone is not completion.
Future production should take explicit data through a canonical deterministic
implementation instead of asking an LLM to reconstruct the code each time.

## Inputs and parameters

Express these parameters in the skill invocation or accompanying instructions;
they are not shell switches for the read-only Python helper.

| Input | Default / behavior |
| --- | --- |
| Scope | Current authorized project; explicit paths narrow the scan and writes. Respect project instructions and exclusions. |
| Asset kinds | Consider snippets, templates, macros, codegen, modules, libraries, and components; honor a requested subset. Produce only kinds justified by actual code. |
| Constraints | Preserve language, native generator/editor/build conventions, existing APIs, licenses, and generated/manual ownership. |
| Preview / audit | Explicit preview, dry-run, plan-only, or audit stays read-only. Ordinary `init` implements eligible in-scope extractions. |
| Work limit | Honor requested time/asset/path limits; report completed assets and remaining candidates accurately if a limit is reached. |
| Concurrency | Use project limits, otherwise at most four independent expensive operations. One writer per asset/caller and one catalog owner; stable fan-in. The evidence helper's `--jobs` contract is separate. |

Exclude unrelated histories, credentials, generated output, caches, vendored
dependencies, and copied worktrees from repetition evidence. Explicit
third-party adaptation retains actual license/provenance obligations.
Init authorizes in-scope extraction and necessary caller migrations. Package
publication, global editor/home changes, and unrelated rewrites require their
own task scope.

## 1. Inspect actual production paths

Read instructions, manifests/build files, source layout, existing snippets,
templates, macros, generators, modules, and tests. Query the existing registry
first, including `.tkstack/reuse/catalog.json` when present. Use `rg --files`/`rg` for
bounded discovery, installed language parsers/AST tools for structural facts,
and a suitable existing clone detector when useful. No new detector framework
is required just to initialize a project.

Textual/AST matches are candidates, not equivalent intent. Record actual
paths/ranges, common behavior, real variations, owners, and behavior evidence.
Use `reusify.py assess` for bounded hashed observations when useful; its count
does not prove extraction safety. Physical aliases, generated copies, and
intentionally repeated test fixtures are not independent implementation uses.

Reuse suitable existing assets immediately. Otherwise prioritize repeated
manual code production: three independent uses or an upcoming third normally
trigger extraction. Init is a direct extraction request, so a clear canonical
pattern can be extracted earlier; retain the smaller evidence base accurately.
Do not manufacture one asset of every kind.

## 2. Define a small extraction contract

For each eligible pattern, record source hashes/callers, invariant, variations,
asset kind/destination, native engine, input schema/defaults, outputs, errors,
ownership, and real verification commands. Prefer deterministic rules/tools for
these facts. Use inference only for unresolved semantic/design choices, then
encode the decision in code, types, parameters, or native configuration.

Choose by update behavior using [authoring](authoring.md): shared modules when
fixes should propagate; snippets for editable forms; templates for parameterized
source; [macros](macros.md) for justified native syntax expansion; compiler/build
generators for mechanical model-to-source derivation. Prefer existing engines
and preserve generated/manual boundaries, deletion, and upgrade behavior.

Independent assets can be extracted concurrently into disjoint writable paths
with private validation outputs. Order overlapping caller migrations explicitly.
Reread hashes before editing and reconcile stale sources. Merge catalog entries
through one owner after stable fan-in. Honor real dependency boundaries rather
than serializing all independent extraction work.

## 3. Extract, wire, and register

Create the smallest native asset and migrate applicable callers or their
generation path. For templates/snippets, preserve intentionally editable copies
and document regeneration; do not replace runtime calls blindly. For macros
and codegen, integrate the actual compiler/build/expansion path and required
imports/types/annotations. Preserve current contracts and legitimate variation.

Separate fixed invariants from validated data inputs. Implement escaping, path
containment, naming, stable ordering/identifiers, incremental cache keys, and
bounded mutable state in code. Normal regeneration must not ask a model to
rewrite a generated body or interpret catalog prose as an algorithm. Isolate
any inherently probabilistic step and identify its lost guarantees explicitly.

Register skill-owned discovery metadata in `.tkstack/reuse/catalog.json` using
the [catalog contract](catalog-and-validation.md). Wire authored code into the
project's native module/package/component registry when needed.
Link each actual artifact, native command/import, supported inputs/outputs,
owner/version, limitations, and proof. Catalog usage strings remain display
data; never execute them blindly. Add a short scoped instruction pointer only
when needed for discovery, using `instructify` when available. Keep the
implementation canonical rather than copying it into every instruction file.

## 4. Verify deterministic production

Run the real native generator/compiler/expander/runtime when available. Check
the original cases, a distinct variation, and a negative/boundary input.
Compare caller behavior before/after; compile or consume emitted code rather
than checking file existence. Repeat unchanged inputs and compare output bytes
or the native normalized contract. Where concurrent use is intended, verify two
invocations with isolated destinations and no shared scratch-path races.

Keep receipts tied to source/input/tool versions. Distinguish source-format
inspection from native execution; missing hosts and failing behavior remain
explicit. Fix or roll back failed migrations within scope. Validate catalog
metadata and discover each new asset through the route a future agent will use.

An existing suitable asset can satisfy initialization: verify its interface,
discovery, and uses instead of duplicating it. If there is no justified
extraction, report the examined scope and evidence. Preview returns the concrete
plan without changing assets, callers, catalogs, or instructions.

Finish with created/reused assets, source cases/migrations, invocation examples,
actual verification, native evidence gaps, and any bounded/incompatible
candidates. Do not claim whole-scope completion beyond inspected work, or
measured inference/token savings without a comparison.

## Examples

- `/reusify init src`: extract eligible assets in `src`, migrate applicable uses,
  register and verify their production path.
- `/reusify init src/ui; templates and components only; preview`: return a
  read-only extraction plan for that subset.
- `/reusify init packages/service; preserve the existing Roslyn generator`:
  reuse/extend its native incremental pipeline.

These are skill requests, not a claim that extraction has already run on this
dotfiles repository. The bundled Copier example separately demonstrates native
deterministic production with explicit validated inputs.
