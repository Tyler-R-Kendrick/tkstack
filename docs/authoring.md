# Reusable skill, code, lint, hook, instruction, and workflow authoring

The canonical packages are [`codify`](../skills/codify/SKILL.md),
[`skillify`](../skills/skillify/SKILL.md),
[`reusify`](../skills/reusify/SKILL.md), [`lintify`](../skills/lintify/SKILL.md),
[`hookify`](../skills/hookify/SKILL.md), and
[`instructify`](../skills/instructify/SKILL.md), and
[`flowify`](../skills/flowify/SKILL.md). All install in Codex, Claude Code, and
Cursor and are separate root marketplace entries. They follow the personal
deterministic-first and concurrency principles.

Use `/codify <prompt-or-markdown>` to lower a procedure once into native code
and freeze a verified executable lock. It owns the shared workflow templates,
compiler/runner, and optional inference runtime extracted from Skillify.
Skillify consumes its generated standalone release for skill packaging. Future
runs execute the frozen artifact and fail on stale inputs; they do not silently
rebuild or interpret prose. See [Codify](codify.md).

## Skillify

Use `/skillify <workflow>` or `$skillify` to turn an explicit request or
demonstrated procedure into an executable workflow in a portable skill's
`scripts/`. The skill is an intermediary code-mode prompt and invocation index,
not the main executable. It also supports adapting a
specified source or updating an owned package. It checks for existing skills,
retains actual evidence and licensing, puts deterministic work in helpers,
and makes the main `SKILL.md` a table of contents/index. Link directly to main
topics, features, optional subcommands, and parameter contracts; keep detailed
tool usage/contracts/rationale in `references/` and load only the selected branch.
Run the tool rather than reconstructing its algorithm through inference.

```sh
python3 skills/skillify/scripts/skillify.py scaffold \
  --target /repo/skills/inspect-contracts --name inspect-contracts \
  --description 'Inspect consumer/provider contracts when asked about compatibility.'
python3 skills/skillify/scripts/skillify.py convert /repo/skills/existing --backend ai-sdk --dry-run
python3 skills/skillify/scripts/skillify.py check /repo/skills/inspect-contracts --require-tool
```

The scaffold creates that index, four linked topic/tool pages, a script-backed
workflow/CLI starter, and a license. `convert` safely seeds an existing owned
skill migration. Complete its actual algorithm and verification before delivery.
The optional `--backend ai-sdk` supplies TypeScript, a native tool export, and
locked Vercel AI SDK profiles for model providers, Decisions, and harnesses.
See [conversion, configuration, and evidence](skillify.md).
`check` reads metadata, resources, local inline links and Python syntax in a
restricted portable profile. It neither executes scripts nor proves behavioral
or trigger quality. See [the exact profile](../skills/skillify/references/validation.md).
Use real behavior tests for observable helper contracts and actual artifact
review for semantic quality. Existing `learn improve` and SkillOpt processes
remain in place for evidence-backed automatic revision/adoption.

## Reusify

Use `/reusify <pattern>` or `$reusify` for reusable code assets. Look up existing
assets first. At three verified occurrences, or before a requested third use,
create/use the smallest appropriate template, snippet, native generator,
module/library, or component. Preserve real variation and the current scope;
an audit request does not authorize an unrelated refactor.

Use `/reusify init [scope]` to extract and register actual code-production
assets across a codebase, including snippets, templates, macros, generators,
and shared code. Ordinary init implements eligible extractions and applicable
migrations; explicit preview stays read-only. Later uses invoke native engines
with validated inputs instead of asking a model to reconstruct the code.
See the [init procedure and parameters](../skills/reusify/references/init.md).

```sh
python3 skills/reusify/scripts/reusify.py find --project . --query "skill scaffold"
python3 skills/reusify/scripts/reusify.py check --project .
```

The project catalog links actual existing assets and their interfaces. The
helper is read-only and never executes usage strings or claims semantic clone
detection. Detailed references cover native T4, Copier/Jinja, snippets, Roslyn
incremental generation, shared-code boundaries, migration, and proof. See
[the guide](reusify.md) for native evidence and unverified host boundaries.

## Lintify

Use `/lintify <standard>` or `$lintify` to produce a native CLI rule/config,
scoped diagnostics, meaningful fixtures, and a verified invocation. Reuse the
project's linter and existing rules first. Markdown can describe deterministic
compiled checks with lintbook or semantic model-evaluated checks with GPTLint.
The latter remains probabilistic and needs actual evaluation before a reliable
gate can be claimed.

```sh
python3 skills/lintify/scripts/lintify.py scaffold \
  --backend eslint --target /tmp/my-lint-example
```

The helper also supplies lintbook and GPTLint examples. It creates only a new
isolated package and activates no rule. Native ESLint behavior and GPTLint
parsing/discovery have direct evidence; semantic evaluation and native lintbook
compilation remain unverified. See [the guide](lintify.md) for commands,
runtime requirements, source versions, and exact evidence boundaries.

## Hookify

Use `/hookify <explicit rule>` or `$hookify` to turn a confirmed instruction
into a testable guard. The skill first determines whether a linter, type,
contract, CI gate, or native permission can enforce the invariant directly.
The bundled engine supports literal typed predicates, warn/block actions,
disabled rules, stable aggregation, and explicit error handling, without model
calls, command execution, or transcript reads.

These commands run the demonstration without activating it:

```sh
python3 skills/hookify/scripts/hookify.py check --rules skills/hookify/examples/policy.json
python3 skills/hookify/scripts/hookify.py replay \
  --rules skills/hookify/examples/policy.json --cases skills/hookify/examples/cases.json --jobs 4
python3 skills/hookify/scripts/hookify.py emit --rules skills/hookify/examples/policy.json
```

Replay uses bounded workers and stable case order. The runtime itself has no
shared writable state; policy publication and native configuration updates
remain explicit owned/serialized boundaries. Rules require positive, negative,
unrelated-event, missing-input, and failure cases appropriate to their contract.

The native adapter/emitter supports Claude **PreToolUse** and **Stop** command
hooks. PreToolUse denial can prevent the operation; Stop continuation includes
a reentry guard. PostToolUse is not claimed to undo completed effects. The
portable evaluator can support other harnesses through verified adapters;
native Codex/Cursor event/blocking compatibility is not implied by installing
the skill. See [policy](../skills/hookify/references/policy.md) and
[adapter contracts](../skills/hookify/references/adapters.md).

`emit` returns a settings fragment only. Merge an actual requested registration
at its canonical configuration boundary, preserve unrelated entries, and verify
reload/activation with a harmless native operation when possible. In tkstack,
standing hooks belong in `scripts/setup_integrations.py`'s ownership-aware
configuration path. No demonstration or new standing policy is registered by
installing these skills. New rules are reread per callback only after a working
registration exists.

## Instructify

Use `/instructify <expectation>` or `$instructify` to create, adapt, update,
audit, or remove scoped agent instructions. It places stable working context
in instruction files, routes procedures to `skillify`, routes mechanical
enforcement to code/`hookify`, and preserves correction history through `learn`.

The package contains a portable manifest and an offline plan/apply/check helper.
Explicit project/directory scopes select shared `AGENTS.md`, Claude `CLAUDE.md`,
native Cursor `.mdc`, or Copilot instruction bindings. Shared AGENTS guidance
plus a Claude import avoids copying the same body. Native adapters use explicit
scope/glob metadata; the helper does not guess file attachment from a description.

```sh
python3 skills/instructify/scripts/instructify.py plan \
  --project /repo --input /repo/harnesses/instructions/expectations.json > /repo/.tkstack/instructify/plan.json
python3 skills/instructify/scripts/instructify.py apply \
  --project /repo --plan /repo/.tkstack/instructify/plan.json --dry-run
python3 skills/instructify/scripts/instructify.py apply \
  --project /repo --plan /repo/.tkstack/instructify/plan.json
python3 skills/instructify/scripts/instructify.py check \
  --project /repo --input /repo/harnesses/instructions/expectations.json
```

The manifest must be an actual owned source in the chosen project; the bundled
example is not automatically applied. Owned sections have source identity and
content hashes. Updates preserve unrelated instructions, reject manual edits
inside protected content, preflight all selected inputs, and reject stale plans.
A project writer lock and atomic per-file replacement protect cooperative
updates. Ordinary write failures attempt rollback without overwriting external
edits; crashes and nonparticipating writers remain explicit limits.

`plan --remove` creates a removal plan for the same owned sections. Remove old
bindings before changing a manifest's scope, targets, ID, or source location;
the helper does not track historical destinations. It also refuses symlinked
targets, dedicated native-file collisions, and nonempty Codex overrides that
would shadow a new AGENTS file. See the [manifest contract](../skills/instructify/references/manifest.md)
and [native discovery details and sources](../skills/instructify/references/harnesses.md).

Within tkstack, existing installer-owned instruction pointers remain controlled
by `scripts/steering_adapter.py` and `harnesses/cursor/tkstack-steering.mdc`.
Creating this skill registers no demonstration instructions and rewrites no
unrelated project or home instruction files. Local tests establish file-level
behavior, not native loading or model compliance.

## Flowify

Use `/flowify <procedure>` or `$flowify` to create a reusable executable workflow
using a real DSL and runtime. MAF YAML is the default for tool/code workflows;
Grok's Rust engine uses Rhai with host-specific functions. The skill preserves
an existing suitable project engine instead of forcing a new schema.

The output includes the native definition, deterministic host/bindings, input
examples, dependencies/lock, invocation, and meaningful positive/failure cases.
The helper scaffolds MAF and Rhai packages and distinguishes source inspection,
native validation, and actual execution. Ordinary code handles facts and gates;
agents are reserved for residual judgment. See [the workflow guide](flowify.md).

Use `skillify` for when/how to use a procedure, `reusify` for reusable code
assets, `lintify` for source/artifact
lint-rule authoring, `flowify` for its executable
control/data flow, `instructify` for standing guidance, and `hookify` for event
enforcement. A hook can invoke an authorized deterministic workflow entry point.
Creating these authoring tools does not enable examples or start agents.

## Sources and validation

Anthropic's actual sources are its `skill-creator`, plugin-development skills,
and `hookify` plugin in `anthropics/claude-plugins-official`; older Claude Code
repository plugin links returned 404. Pstack contributes its authoring playbook,
`automate-me`/`reflect`, and structural/shared-state principles. Exact-name
`skillify`/`hookify` skills were not found in the checked Pstack tree. See the
bundled [skillify sources](../skills/skillify/references/sources.md) and
[hookify sources](../skills/hookify/references/sources.md).

These are independently written owned packages. Vendor snapshots remain
unchanged. Local tests establish scaffold collision protection, portable copies,
reference/syntax checks, typed decisions, replay stability, native JSON/exit
contracts, explicit error modes, and Stop reentry. Native Claude execution,
model compliance, and creative-quality improvement are separate claims requiring
their own real evidence; the native Claude CLI is not available in this workspace.
