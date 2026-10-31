# Sources and execution boundaries

This owned skill implements the user's explicit three-occurrence reuse trigger
and lookup-before-reimplementation goal. It uses skillify's package conventions
and tkstack's deterministic-first, bounded-concurrency, minimal-change, and
interface principles. Research does not create new correction evidence.

- [Microsoft T4 overview](https://github.com/MicrosoftDocs/visualstudio-docs/blob/fedd646924b5e9d7986a4af2be669efa5fe0c29f/docs/modeling/code-generation-and-t4-text-templates.md)
  distinguishes design-time file generation from preprocessed runtime templates.
- [Roslyn incremental generator design](https://github.com/dotnet/roslyn/blob/3b229441ea176b34c6ab891eb540f4f52c48c59f/docs/features/incremental-generators.md)
  and [cookbook](https://github.com/dotnet/roslyn/blob/3b229441ea176b34c6ab891eb540f4f52c48c59f/docs/features/incremental-generators.cookbook.md)
  establish immutable pipelines, value-equatable intermediate models, host
  scheduling/caching, additional inputs, native diagnostics, and additive output.
- [Copier configuration](https://github.com/copier-org/copier/blob/18150bd3605a144db86cb87341add7313634f23f/docs/configuring.md)
  documents native questions, validation, template roots, Jinja rendering, tasks,
  and input/update settings. The concrete example targets Copier 9.7.1.
- [VS Code native snippets](https://github.com/microsoft/vscode-docs/blob/af4859a5fb06e699ca687d0bd56367f5ed0f3399/docs/editing/userdefinedsnippets.md)
  establishes JSON snippet scope, prefixes, bodies, and placeholders. Editor
  settings are adapters, not prerequisites for the portable reuse procedure.

Guidance and sample assets are independently authored. The catalog/evidence
helper is standard-library code, not a clone detector, code generator engine,
command runner, or behavioral evaluator. Copier rendering can be checked with
its actual CLI; T4/Roslyn/editor-native claims require their real compatible hosts.
Do not present source inspection or JSON syntax checks as native execution,
compiler incrementality, automatic adoption, or measured inference reduction.
