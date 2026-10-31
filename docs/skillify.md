# Skills compile into executable tools

`skillify` turns a demonstrated procedure or existing owned skill into a
workflow under that skill's `scripts/`. `SKILL.md` is the intermediary code-mode
prompt and invocation index. Future execution supplies typed input to the tool
and inspects output; it does not ask an agent to reconstruct a prose algorithm.

The main page still uses progressive disclosure for topics, features,
subcommands, parameters, contracts, and evidence. Execution, branching, policy
gates, dependencies, bounded concurrency, and error handling belong in code.
Use an existing runtime when it fits; `flowify` remains the owner of MAF/Rhai
authoring. Native definitions and bindings also belong in the skill's scripts
folder. The AI SDK supplies model/decision/harness boundaries, not a new workflow
DSL or an implied durable scheduler.

```sh
python3 skills/learn/skills/skillify/scripts/skillify.py scaffold \
  --target /repo/skills/my-tool --name my-tool \
  --description 'Use for the actual intended task.' --backend ai-sdk

python3 skills/learn/skills/skillify/scripts/skillify.py convert /repo/skills/existing \
  --backend ai-sdk --dry-run
python3 skills/learn/skills/skillify/scripts/skillify.py convert /repo/skills/existing \
  --backend ai-sdk

python3 skills/learn/skills/skillify/scripts/skillify.py check /repo/skills/my-tool --require-tool
```

The pure Python backend is the smallest default for deterministic work. The
AI SDK backend supplies TypeScript workflow/CLI definitions, a native `tool()`
export, configuration validation, and a locked inference runtime. Both begin as
explicit drafts: implement the actual algorithm and native tests before calling
conversion complete. Their unimplemented workflow exits 3. A successful helper
run does not prove a Markdown procedure has been correctly compiled.

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

[Codify](codify.md) now owns the templates, compiler/runner, and optional AI SDK
runtime. Skillify consumes a generated standalone release, checked by doctor.
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

## Model, Decisions, and harness configuration

The version-pinned Vercel AI SDK 7 runtime provides separate interfaces for:

- Chat Completions and Responses through OpenAI-compatible providers, plus
  explicitly selected Gateway language models.
- Native `experimental_decide` calls through OpenAI, TypeSafe, or Gateway
  decision-model instances. This is separate from chat/Responses endpoints.
- Official Codex and Claude Code harness adapters with model, authentication,
  tool/permission selection, bounded steps, and explicit Vercel sandbox setup.

Use [the shared example](../harnesses/ai-sdk/profiles.example.json) as configuration
data, with model/key environment-variable references. The generated CLI accepts
`--config <profiles-json>`; code can supply a configuration to `createInference`.
Profiles are validated, selected explicitly, and have no silent provider fallback
or process-wide default-provider mutation. Runtime defaults are empty and need
no model credentials for deterministic paths.

Calls share a bounded active/queued capacity budget. Deadlines and cancellation
reach the native SDK. A specialized decision model can still be probabilistic;
an LLM behind a decision API is not deterministic. Keep the final policy gate
in workflow code. See [configuration and native limits](../skills/learn/skills/skillify/references/inference.md)
for exact versions, supported profiles, authentication, and harness restrictions.

## Verification

Python regressions exercise real generated tool output, source preservation,
preview scope, collisions, unsafe paths, cooperative writer contention, rollback,
and unfinished-workflow rejection. Optional native tests use the locked Node
dependencies to compile a generated TS skill, invoke its CLI and SDK `tool()`,
check repeatability and negative inputs, and run seven bundled SDK contracts.

The SDK contracts use injected HTTP fixtures through the actual installed SDK:
they check distinct wire endpoints, model/profile selection, invalid decision
responses, cancellation, capacity ownership, and official harness instantiation.
They do not run a paid provider request or live harness session. The native
decision/harness APIs are experimental; upgrades require version-matched checks.

```sh
npm --prefix skills/learn/skills/codify/scripts/ai-runtime ci
npm --prefix skills/learn/skills/codify/scripts/ai-runtime run check
npm --prefix skills/learn/skills/codify/scripts/ai-runtime test
TKSTACK_AI_SDK_DEPENDENCIES="$PWD/skills/codify/scripts/ai-runtime/node_modules" \
  python3 -m unittest discover -s tests -p test_skillify_workflows.py -v
```

The workspace's isolated validation dependencies and receipts are under ignored
`.tkstack/evidence/skillify-runtime/`. Structural profile checks exclude installed
`node_modules`, bytecode caches, and Git internals; they do not traverse third-party
dependency trees as owned skill resources. Real execution and output review
remain separate from source/packaging validation.

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
procedure and coverage; `scripts/check_skills.py` and doctor enforce conformance.
