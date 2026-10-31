# Markdown subcommands and function tools

Define each public subcommand in `commands/<name>.md`. Its YAML frontmatter
declares a tool signature and deterministic local bindings; the Markdown body
documents usage, examples, effects, errors, and completion. Nested commands use
token arrays, so no model must infer the command path. Keep `SKILL.md` an index
with a direct link to each public command and its default/help behavior.

The [versioned document schema](../scripts/command.schema.json) is
`tkstack.command/v1`. Its `tool` field is an OpenAI **Responses** function tool;
`cli` and `run` are local metadata outside that API object. Export only `tool`
to Responses. For Chat Completions, the exporter wraps its function fields in
`{"type":"function","function":{...}}`. Do not send CLI metadata as OpenAI
function fields or invent aliases/flags as JSON Schema keywords.

```yaml
---
schema: tkstack.command/v1
tool:
  type: function
  name: repeat_text
  description: Repeat a bounded text value.
  strict: true
  parameters:
    type: object
    properties:
      text: {type: string}
      count: {type: integer, minimum: 1, maximum: 4}
      loud: {type: boolean}
    required: [text, count, loud]
    additionalProperties: false
cli:
  path: [text, repeat]
  aliases: [[repeat], [text, again]]
  positionals: [text]
  flags:
    count: [--count, -n]
    loud: [--loud]
  defaults: {count: 1, loud: false}
run:
  artifact: scripts/workflow.lock.json
---

# Repeat text

Invoke `text repeat hello -n 2 --loud` or `repeat hello --count=2`.
Describe the actual implementation, output, effects, rejection cases, and checks.
```

This is an illustrative signature; author its matching workflow before using it.
The complete normalization example in Codify's package has real code, contracts,
command definitions, and a compiled lock.

## Author and compile

1. Inspect the workflow's actual input and supported outputs. Prefer existing
   code. Name each command, nested path, aliases, typed parameters, defaults,
   effects, and exceptions from the request rather than inventing switches.
2. Create one command Markdown file per function. Names must be unique; canonical
   paths and all aliases must be unique across the catalog. Bind a parameter
   once as a positional or flag, or give it a CLI default. CLI defaults must
   validate against that parameter's schema. Preserve schema-required API input.
3. Link each definition from the main index. Keep the reserved `help` and
   `version` definitions supplied by the shared templates. Both scaffolding and
   conversion supply them and a **draft** `run` signature;
   replace the draft with the actual input contract before shipping.
4. Run `commands` to validate the catalog and export/check tool signatures.
   Compile the actual workflow with positive, transfer, and rejection cases.
   Codify automatically includes `commands/` under its build root in the lock.
   Metadata is bound to frozen code; no prompt interpretation occurs at dispatch.
5. Invoke through CLI and both tool-call shapes and compare real outputs.
   Exercise aliases, defaults, flags, invalid input, and read-only help. Preserve
   existing native raw-JSON interfaces where they remain useful.

## Invoke the shared interface

From a generated package root with its command dependencies available:

```sh
python3 scripts/codify.py commands .
python3 scripts/codify.py commands . --format responses
python3 scripts/codify.py commands . --format chat
python3 scripts/codify.py invoke .                 # default console manual
python3 scripts/codify.py invoke . -- help
python3 scripts/codify.py invoke . -- help --format man
python3 scripts/codify.py invoke . -- version
python3 scripts/codify.py invoke . -- text repeat --help
python3 scripts/codify.py invoke . -- repeat hello -n 2 --loud
python3 scripts/codify.py invoke . --call /path/to/tool-call.json
```

For a source package or another directory, use that package's `codify.py`
or `skillify.py` and replace `.` with the authored package directory.
`commands` and `invoke` use the same canonical engine in both skills. Managed
dotfiles installs also provide `codify` and `skillify` command shims backed by
the private hash-locked command runtime.

Tool calls may use a Responses `function_call` with `name` and JSON-string
`arguments`, a Chat tool call with `function: {name, arguments}`, or the direct
`{name, arguments}` shape with a JSON string or object. `--call -` reads stdin;
it is exclusive with CLI arguments. The application remains responsible for
authorizing a tool call before dispatch. This interface calls no model or API.

String parameters accept literal CLI text; integers, numbers, arrays, objects,
and general union types accept JSON tokens. Nullable strings also accept literal text. For example, pass arrays as
`--labels '["a","b"]'`. Pure boolean flags accept `--loud`/`--no-loud`;
short aliases share their parameter. `--` separates dispatcher options from
the selected command. Abbreviated flags are rejected. The longest exact path
selects a nested command; a group path lists its children. Unknown commands or
help topics fail explicitly. An omitted positional can use a declared default;
missing required values are rejected by the same schema used for tool calls.

CLI and tool arguments validate **before** any workflow invocation. Successful
dispatch checks the lock's freshness and verifies this exact command file was
included in that lock, then executes the frozen code. Missing bindings, changed
signatures/bodies, and changed code/cases require explicit recompilation.
Workflow exit/output propagate; there is no fallback to live code or inference.

Help, version, export, and validation do not initialize state, scan sessions, or
invoke a workflow. Discovery works without a lock. All executable commands bind `run.artifact`
to a contained, nonsymlinked lock path. There is no shell command binding.
Parser usage errors exit 2; invalid metadata/arguments or stale bindings exit 1.
Real execution uses the existing bounded deadline and isolated session runner.

## Reserved help and version

The runtime owns top-level names/routes/aliases `help` and `version`, plus
`--help`/`-h` and `--version`/`-V`. A workflow cannot claim them. Their Markdown
files document and expose the standard builtin signatures; do not bind them to
an artifact or change their names, parameters, or CLI bindings. Older command
packages that omit these files receive the default signatures automatically
when their catalog is loaded. An absent file has `file: null` in the command
index, distinguishing a runtime-provided builtin from an authored command.

The help tool has `run: {builtin: help}`, path `[help]`, and strict required
parameters `topic: {type: [string, "null"]}` and
`format: {type: string, enum: [text, man]}`. CLI defaults are null topic and text
format. `help [command ...]`, a command/group's `--help`, and omitted commands
render the corresponding manual with the same canonical paths and content.
Use `help tasks claim` or API `topic: "tasks claim"` for nested topics. Unknown
topics fail. Existing authored topic-only help signatures remain supported with
text as their implicit format; their API calls retain that older shape.

Help builds one man-page model from the package identity, description, command
body, aliases, flags, defaults, and full parameter constraints. The same model
generates escaped man(1) roff source and deterministic console text, with NAME,
SYNOPSIS, DESCRIPTION, COMMANDS or OPTIONS/TOOL PARAMETERS, EXIT STATUS, and
VERSION sections. Console wrapping is fixed and uses no terminal probing,
color, pager, locale-dependent formatter, date, file modification time, or
model. Roff escapes backslashes, hyphens, and leading requests; console output
makes control characters visible. The renderer handles this generated profile,
not arbitrary externally supplied roff. Markdown bodies use a small plain-text
conversion for headings, links, inline code, and fenced code; no host Markdown
or man program is invoked.

`help --format man` prints source for export, for example
`codify.py invoke . -- help --format man > my-tool.1`. CLI help prints its page
directly. API help returns JSON with `help` (selected output), `man` (source),
`format`, `name`, and `version`; CLI and API text/source values match.

Version uses `run: {builtin: version}`, path/name `version`, and an empty strict
parameter object. `version`, `--version`, `-V`, and a command's `--version`
print `<name> <version>`. API version returns `{name, version}`. Name/description
and the string `metadata.version` come from `SKILL.md`. Plain workflow packages
use their directory name and report `unversioned`; a missing version is never
invented. Version describes package metadata, not artifact freshness or a Git
revision. Use the existing `check` interface for compilation readiness.

## Schema profile and dependencies

The portable profile uses OpenAI strict function tools: an object root, all
properties required, and `additionalProperties: false` on every object.
Optional API values use a nullable type while remaining required. CLI defaults
are local conveniences and are not injected into API tool calls.

Supported inline schemas include JSON primitives, nested objects/arrays,
`anyOf`, nullable type arrays, enums/constants, numeric bounds/multiples, string
length/pattern constraints, and array length bounds. Local validation uses
Draft 2020-12. The profile rejects references, recursive schemas, format
annotations, arbitrary JSON Schema extensions, and schemas deeper than ten
levels instead of silently dropping them. Provider/model limits may be narrower;
an offline export is not a claim that a live provider accepted the schema.
YAML must be safe and JSON-compatible, with unique string keys and no aliases
or custom tags. Maximums: 128 command files and 256 KiB per Markdown definition.

CLI nullable string parameters accept ordinary unquoted text, including paths.
The literal `null` selects JSON null; pass `'"null"'` for the string `null`.
Explicit JSON-quoted strings are decoded. Other non-string values use JSON
syntax. API tool arguments retain their declared JSON types without CLI coercion.

PyYAML 6.0.3 and jsonschema 4.26.0 plus their transitive dependencies are pinned
with hashes. Root dotfiles bootstrap installs them privately as `command-schema`.
Generated packages carry `scripts/requirements-commands.lock`; if needed, from
that package directory, explicitly initialize an isolated environment:

```sh
tkstack_runtime_root="$(python3 scripts/tkstack_state.py init --namespace runtime)"
tkstack_commands_dir="$tkstack_runtime_root/commands"
python3 -m venv "$tkstack_commands_dir"
"$tkstack_commands_dir/bin/python" -m pip install --require-hashes -r scripts/requirements-commands.lock
"$tkstack_commands_dir/bin/python" scripts/codify.py commands .
```

Keep that environment in the selected ignored `.tkstack` scope. Codify's source
package uses `requirements/requirements.lock`; Skillify carries its generated
copy under `scripts/codify_runtime/requirements/`. Missing dependencies are
reported; discovery never implicitly downloads them. Direct raw-JSON Python
workflow execution and ordinary Codify locks without commands retain their
existing standard-library interface.

Primary contracts: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling),
[Responses FunctionToolParam](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/function_tool_param.py),
and [Chat function definition](https://github.com/openai/openai-python/blob/main/src/openai/types/shared_params/function_definition.py).

## Normalized owned skill cores

Skillify's explicit `normalize` operation supplies `model`, `verify`, and typed
`native <operation>` commands from `scripts/contract.json`, alongside reserved
help/version. The contract uses JSON Schema, concrete criterion descriptions,
and declared native argument bindings. It is data for an existing Python
runtime, not a new workflow DSL or an implicit model/provider selection.

`model` exports that contract and its semantic/native limits. `verify --report`
checks actual retained file hashes, criterion coverage, constrained facts and
recorded review, explicitly returning `recorded-not-authenticated` for semantic
inspection. Domain-native gates still apply. Native bindings call the existing
contained helper without shell strings and preserve its stdout/exit status;
raw JSON inputs receive the same schema validation before effects. Relative
paths use the selected workspace. Compiled invocation uses ignored temporary
materialization and requests no implicit inference; explicit native compilation
or artifact execution retains the supplied code's own effects/profiles.

The common compiler/command/runtime JSON reader rejects duplicate fields,
non-finite literals and overflowing JSON numbers. Shared runtime copies and
source-generation manifests are verified by the repository conformance gate.
