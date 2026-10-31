# 0011: Share Markdown command signatures and compiled invocation

Status: accepted, 2026-10-30.

The user requested subcommands defined in Markdown with YAML frontmatter using
OpenAI function-tool schemas, shared by Skillify and Codify. Separate prose-only
command lists leave aliases, parameters, and executable invocation to inference.

Use `commands/<name>.md` with the versioned `tkstack.command/v1` document schema.
Its `tool` is an OpenAI Responses strict function definition; `cli` contains
local command paths, aliases, positionals, flags, and defaults; `run` binds a
compiled artifact. Chat exports use its native nested function wrapper. Keep
local metadata outside API tools and use one canonical function name per tool.

Codify owns safe YAML parsing, JSON Schema validation, metadata checks, exports,
and CLI/tool-call dispatch. Skillify teaches the format, validates catalogs,
and generates standalone copies through its existing Codify release mechanism.
Scaffolds/conversions include help and a draft workflow command; authors must
complete the actual input contract, code, cases, and command documentation.

Command definitions are included in compilation and bound to the lock inventory.
Invocation validates parameters, checks freshness and the exact command hash,
then executes frozen code through the existing isolated bounded runner. Help
and exports remain read-only and available without compilation. No shell text,
arbitrary session commands, implicit model call, or automatic recompilation is
introduced. Application callers still own authorization for actual effects.

Use a documented inline strict-schema profile rather than silently accepting
unsupported references or annotations. PyYAML/jsonschema and dependencies are
hash-locked and installed privately by dotfiles bootstrap; managed Codify and
Skillify shims use that interpreter. Standalone generated packages carry their
dependency recipe, schema, runner, license, and command reference.

Verification includes real CLI/API outcome parity, aliases, nested paths,
boolean/numeric/JSON values, defaults, explicit invalid input, stale metadata,
unsafe YAML/path rejection, standalone copies, and concurrent isolation.
The working normalization example demonstrates both API exports and execution.
No live model/provider call is required to establish these local contracts.
