# Roslyn and compiler-integrated generation

Use compiler generation for declarations mechanically derived from source
metadata, attributes, schemas, or additional files. Prefer ordinary shared code
when no generated source is necessary. Use a language's actual native compiler
API; Roslyn-specific APIs are an adapter for C#, not a harness dependency.

For Roslyn, implement `IIncrementalGenerator` and define the dataflow in
`Initialize(IncrementalGeneratorInitializationContext)`. Prefer focused attribute
discovery with `ForAttributeWithMetadataName` when it fits. Use a cheap syntax
filter before semantic work; transform symbols into small immutable, value-
equatable models early. Do not retain `Compilation`, symbols, or syntax trees
in long-lived output models or mutable static fields.

Model equality is part of the incremental contract. Records do not magically
give array/list elements structural equality. Use suitable immutable values
and explicit comparers when needed, so unchanged information stops downstream
work. Avoid broad `CompilationProvider` combinations or `Collect()` when each
item can be generated independently. Aggregate only for a real cross-item rule.

Emit with `RegisterSourceOutput` and stable unique `AddSource` hint names.
Validate identifiers, escape literals with a suitable language-aware API, handle
duplicate generated names, and produce native diagnostics for unsupported input.
Keep authored and generated code separate, often with `partial` declarations.
Use the generator's actual analyzer reference/package contract; an ordinary
runtime reference alone does not register a compiler generator.

Transforms should be deterministic, cancellation-aware, and safe for host
concurrency. Let Roslyn own scheduling and caching; do not start uncontrolled
threads, depend on callback order, perform hidden network access, or use mutable
per-project state on a generator instance. Independent generators run unordered
and cannot rely on another generator's newly emitted output in that same pass.

Roslyn source generation is additive. It does not rewrite existing source, IL,
or call sites. Use a real codemod/refactoring mechanism when that is the task.
Do not promise a new language dialect or an interception feature without its
actual supported compiler/host contract.

Validate with a real consumer compilation and the native generator driver:
original three cases, a genuinely new shape, invalid/duplicate inputs, generated
diagnostics, unchanged reruns, unrelated edits, relevant edits, and cancellation
as applicable. Retain/reuse the driver across runs and inspect tracked incremental
steps when claiming recomputation was avoided. Equal output alone does not prove
incremental caching or a performance improvement.

Pin supported SDK, compiler/Roslyn API, target frameworks, dependencies, and
analyzer packaging. Include consumer usage and actual build/test commands with
the published generator. The source references were reviewed for this skill;
no native T4/Roslyn execution is claimed without a compatible installed host.
