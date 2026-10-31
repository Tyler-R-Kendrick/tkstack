# Teach a skill its command surface

Use one `commands/<command>.md` file for each public subcommand. Its YAML
frontmatter carries an OpenAI Responses function tool, separate CLI bindings,
and its compiled artifact binding. Markdown documents the command's procedure.
Use the shared [signature, schema, and invocation contract](../scripts/codify_runtime/references/command-definitions.md)
and [document schema](../scripts/codify_runtime/scripts/command.schema.json).
Codify owns this implementation; do not write a second parser or dispatcher.

1. Map actual subcommands, nested paths, aliases, positional parameters, flags,
   defaults, and effects. The main `SKILL.md` links each command directly and
   states what happens when a command is omitted: reserved help.
2. Scaffold/convert supplies reserved `commands/help.md` and
   `commands/version.md`, a draft `commands/run.md`,
   schema, lock runner, dependency recipe, and referenced usage. Replace the
   draft parameter schema with the workflow's actual contract; add command files
   only for real supported operations. Preserve existing commands when updating.
   Keep the reserved signatures and builtin bindings intact. The shared runtime
   supplies them for an older command package whose files omit them. Reserve
   top-level names/routes/aliases `help` and `version`, and flags `--help`/`-h`
   and `--version`/`-V`, instead of assigning them to workflow code.
3. Keep flags/aliases/path/defaults under `cli`, execution under `run`, and only
   standard OpenAI fields under `tool`. Make nested objects strict and preserve
   nullable required API parameters. CLI defaults must validate. Index full
   parameter details through the command files rather than copying manuals.
4. Validate with `skillify.py commands <directory>` or `check`. Compile the
   matching implementation/cases; definitions are included automatically. Use
   `skillify.py invoke <directory> -- <command> [arguments]` or `--call` to execute
   the same code through CLI/API inputs. Export Responses/Chat tool definitions
   with `commands <directory> --format responses|chat`.
5. Prove aliases, nested paths, typed flags/defaults, tool-call parity, help/version,
   invalid parameters, and stale-signature rejection. A parser, scaffold, or
   schema alone does not prove the workflow. Keep help/preview read-only and
   preserve existing authorization for actual effects and residual inference.

Help generates one man-page model from package metadata, command frontmatter,
descriptions, body, aliases, parameters, flags, defaults, and constraints.
`help [command ...]` and `<command> --help` render the same canonical page using
fixed console rules. `help --format man` emits escaped man(1) roff source for
export. No terminal-width probe, host pager/formatter, timestamp, model call,
or state initialization affects rendering. Version reports `metadata.version`
from `SKILL.md`; absent metadata is explicitly `unversioned`. It does not assert
that an executable artifact is current. API help returns console/source text in
JSON, while CLI help prints the page directly. Read the shared contract for the
exact strict signatures and compatibility with the previous topic-only tool.

Generated packages include their own `scripts/codify.py`, command engine,
schema, hash-locked dependencies, licenses, and referenced usage. They do not
need the original dotfiles checkout or an installed sibling skill. Their main
workflow still needs its real implementation and verified lock before release.
