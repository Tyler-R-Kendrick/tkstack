# Skills compile into executable tools

For a guidance-only procedure, use `metadata.kind: guidance` and validate the Markdown package. Reserve executable normalization for a command contract. [Package kinds](normalization.md).

`skillify` turns a demonstrated procedure or existing owned skill into a
workflow under that skill's `scripts/`. `SKILL.md` is the intermediary code-mode
prompt and invocation index. Future execution supplies typed input to the tool
and inspects output; it does not ask an agent to reconstruct a prose algorithm.

The main page still uses progressive disclosure for topics, features,
subcommands, parameters, contracts, and evidence. Execution, branching, policy
gates, dependencies, bounded concurrency, and error handling belong in code.
Use an existing runtime when it fits; `flowify` remains the owner of MAF/Rhai
authoring. Native definitions and bindings also belong in the skill's scripts
folder. Semantic work stays with the invoking agent and its current model and harness.

```sh
python3 skills/learn/skills/skillify/scripts/skillify.py scaffold \
  --target /repo/skills/my-tool --name my-tool \
  --description 'Use for the actual intended task.'

python3 skills/learn/skills/skillify/scripts/skillify.py convert /repo/skills/existing \
  --dry-run
python3 skills/learn/skills/skillify/scripts/skillify.py convert /repo/skills/existing \


python3 skills/learn/skills/skillify/scripts/skillify.py check /repo/skills/my-tool --require-tool
```

The Python backend produces a draft. Implement the actual algorithm and
native tests before calling conversion complete. An unfinished workflow exits 3.

The bundled shared dispatcher accepts ordinary text for nullable string flags
(including paths), `null` for absence, and JSON-quoted strings when needed.
CLI and API calls still validate against the same strict parameter schema.

Scaffold and conversion provide reserved `help` and `version` command files and
the shared deterministic implementation. Omitting a command displays a console
manual generated from package metadata and command signatures. `help --format
man` exports man(1) roff source; nested help and aliases use that same page model.
`version`/`--version` report the declared `metadata.version`, or `unversioned` if
absent. Both work without a lock, model, terminal formatter, or state writes.
Workflow code cannot override these names, routes, aliases, or global flags.
See [the reserved command contract](../skills/learn/skills/codify/references/command-definitions.md#reserved-help-and-version).

Conversion preserves exact prior Markdown as authoring data, retains frontmatter
and license, rejects collisions, and updates the main file to document invocation.
Adapt an existing fitting executable directly instead of overwriting it with a
starter. See [the conversion contract](../skills/learn/skills/skillify/references/executable-workflows.md)
and [helper commands](../skills/learn/skills/skillify/references/commands.md).

## Shared compiler and executable lock

[Codify](codify.md) owns the deterministic templates and compiler/runner. Skillify consumes a generated standalone release.
`python3 skills/learn/skills/skillify/scripts/sync_codify.py --check` rejects
drift between that release and canonical Codify source.
After implementing the workflow and real contract cases, run:

```sh
python3 skills/learn/skills/skillify/scripts/skillify.py compile /repo/skills/my-tool \
  --cases /repo/skills/my-tool/cases.json
python3 skills/learn/skills/codify/scripts/codify.py run /repo/skills/my-tool/scripts/workflow.lock.json --input input.json
```

The lock freezes exact executable bytes and source/case provenance. Runtime
checks reject drift, execute the frozen code, and never compile implicitly.
Skill-specific source preservation/indexing stays with Skillify; generic
prompt/Markdown compilation can be reused independently through Codify.

## Host inference and verification

The invoking agent supplies semantic judgment in its current conversation.
Skillify does not scaffold a second agent runtime or select another model.
Legacy inference profiles are rejected before compiled execution. Native
behavior, stale-source rejection, process deadlines and the actual artifact
still require focused verification.

## Markdown subcommands and OpenAI tool signatures

Skillify 0.7.0 teaches and scaffolds `commands/<name>.md` files with YAML
frontmatter conforming to OpenAI Responses function tools. Separate `cli` metadata
declares nested paths, aliases, positionals, typed flags, and defaults; `run` binds
the verified lock. Commands remain direct links in the main skill index.
Scaffold/convert includes help, a draft run signature, the shared runner/schema,
locked dependencies, and referenced usage. Complete the actual workflow contract.

Use `skillify.py commands <package> --format responses|chat` to export tools, and
`skillify.py invoke <package> -- <command> [arguments]` or `--call <tool-call.json>`
to invoke the same compiled code. Metadata and code drift require recompilation.
Read [the authoring procedure](../skills/learn/skills/skillify/references/subcommands.md) and
[shared signature contract](../skills/learn/skills/codify/references/command-definitions.md).

## Normalize an existing owned skill

Use `normalize <directory> --profile <contract.json> --dry-run` to review the
shared model/verify/native interface, then apply the same command. The explicit
profile describes real domain constraints, evidence criteria, native bindings
and residual semantic limits. Native helper policy stays with its original code.
Generation tracks relative owned output hashes and rejects modified generated
sources before overwrite/removal. Recompile actual code/cases after changes.
[All-skill normalization and maintenance](normalization.md) contains the complete
procedure and coverage; `python3 skills/learn/skills/skillify/scripts/sync_codify.py --check`
and `src/check_skills.py` enforce the release-copy and skill-conformance gates.

Route a request for a distinct behavioral test to `/learn testify`; use
Skillify when the durable artifact is a reusable agent procedure or skill.
