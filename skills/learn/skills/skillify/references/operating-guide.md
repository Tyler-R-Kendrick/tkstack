# Skillify

Compile a useful procedure into the smallest executable tool package. Establish its
observable outcome, trigger, inputs, boundaries, and verification. Apply
tkstack's deterministic-first and concurrency principles when available; do not
make an agent repeatedly infer a check that executable code can perform.

This workflow draws on Pstack's authoring/`automate-me`/`reflect` procedures and
Anthropic's skill-creator and plugin development skills. The
[source notes](../references/sources.md) distinguish the actual analogues and our
adaptations. This is an owned implementation, not a renamed vendor package.

## 1. Resolve the requested operation

| Explicit signal | Operation |
| --- | --- |
| New workflow or "turn this into a skill" | Create from the visible demonstrated procedure and requested outcome |
| A named external skill/source to adapt | Adapt into an owned package; retain source revision and license obligations |
| A named owned skill to fix or extend | Update that canonical package with a bounded diff |
| Audit, evaluate, report, or draft only | Produce the requested review/candidate without changing active installation |

Use the stated target and current conversation before asking questions. Inspect
the closest existing skills and references; update a fitting owned skill instead
of adding a duplicate. Do not infer overwrite permission from a directory name.
Keep a source baseline for an update and reconcile concurrent drift before writing.

Use only visible conversation, supplied files, explicitly scoped transcripts,
and actual task artifacts. Preserve user corrections through `learn` and task
observations as experiences when available; do not invent evidence or scan
unrelated private histories. An explicit new preference can be incorporated
immediately within the requested scope without demanding repeated confirmation.

## 2. Choose the durable mechanism

Code templates, snippets, generators, reusable modules/libraries, and components
belong in `reusify` when available. Reuse an existing asset before inventing
another implementation. Three verified occurrences or a requested third use
trigger the reuse procedure; a direct asset request can start earlier.

Put repeatable algorithms, schemas, fact queries, routing, exit-code gates, and
state transitions in scripts/types/contracts. Use a skill to explain when and
how to run them. Mechanically detectable recurring behavior may belong in a
lint, CI check, or `hookify` guard instead of another prose reminder. Use
`lintify` when available for native CLI lint-rule authoring; `hookify` owns
actual tool-event guards rather than duplicating the lint implementation.
Stable working expectations or scoped agent context belong in `instructify`
when available; keep reusable procedures here instead of duplicating their
full steps in startup instruction files.
Use `flowify` when available for native workflow DSL design, while `codify` owns prompt/Markdown compilation and locked execution.
Skillify owns skill packaging and invokes a generated standalone release of Codify. Store actual definitions/bindings
in the skill's `scripts/`. Markdown is the intermediary code-mode prompt and
tool index; state transitions and readiness gates execute in code rather than
repeated agent interpretation. See [conversion](executable-workflows.md).

For each substantive judgment, try code/rules first, a fit-for-purpose decision
model/API next, and an LLM/agent only for the unresolved part. Define outputs,
failure/unknown behavior, and deterministic validation. Generated prose or a
model consensus must not bypass an objective gate.

Keep independent steps and assets separable with explicit dependencies and
owners. Batch independent lookups; bound expensive work. Parallel agents, if
authorized, need isolated writable targets. A single package/publication boundary
still has one owner. Do not add worker pools to trivial pure helpers.

## 3. Author the owned package

Default to root `skills/<kebab-name>/` in the authorized repository. Preserve an
existing canonical path. Do not edit `vendor/`, generated alias views, another
plugin's cache, or home configuration as an incidental authoring step.

Include `SKILL.md`, its license, and only supporting files the procedure needs.
Define each real subcommand in `commands/<name>.md` using the shared
[OpenAI signature and local binding contract](subcommands.md). Teach the skill
to select exact paths/aliases and validate typed parameters rather than infer
flags. Supply default read-only help. Link every command from the main index,
complete its body and actual parameter schema, and use Codify's shared dispatcher
for CLI and function-call invocation into a verified lock. Skillify supplies
reserved help/version definitions and the shared implementation. Keep default
help read-only, render its generated man page deterministically, expose man(1)
source with `help --format man`, and report the declared package version with
`version`. Do not assign their names, routes, or global flags to workflow code.
Make the main file a code-mode prompt and index/table of contents with direct,
conditional links to tool invocation, topics, features, optional subcommands,
and input/parameter contracts. Put the executable workflow in `scripts/`;
keep tool usage, contracts, rationale, and evidence in `references/`. Follow
the [index design rules](progressive-disclosure.md).
The description must say both what the skill does and when to select it.
Distinguish a user-invoked workflow from an automatically applicable one. Declare
actual tool/capability requirements and behavior when they are unavailable.

The optional scaffold refuses to replace an existing directory:

```sh
python3 <skillify-directory>/scripts/skillify.py scaffold \
  --target /repo/skills/inspect-contracts --name inspect-contracts \
  --description 'Inspect consumer/provider contracts when asked to review compatibility.'
```

The result is an incomplete **draft**: an index, four linked topic/interface
pages, a script-backed workflow and CLI, and a license. Pure Python is the
smallest default for deterministic work. Select `--backend ai-sdk` for
TypeScript with the locked Vercel AI SDK runtime, native tool export, and
explicit language/Decisions/harness profiles. Replace placeholders and implement
the actual procedure in `scripts/workflow.*`. Complete the callable interface
and native verification before delivering; add command pages when appropriate.
The bundled MIT license is suitable for this
repository's new owned work; use the actual applicable license and attribution
when adapting third-party material. Do not silently relicense upstream content.

Encode ordered/dependent operations, decision gates, recovery/rollback, bounded
concurrency, and completion in executable definitions. Document prerequisites,
input/output contracts, reason codes, artifacts, and invocation. Use `convert`
to seed an owned skill migration, then finish its actual behavior using the
[executable workflow procedure](executable-workflows.md).
Reference other skills conditionally when optional so a standalone copy remains
usable. Keep provider-specific installation in an adapter/reference rather than
copying one harness's assumptions into every workflow.

For an existing owned package, model its actual fact constraints, evidence criteria,
native bindings and residual semantic boundaries. Use `normalize <directory>
--profile <contract.json> --dry-run`, review the generated diff, then apply that
same normalizer. It reuses the canonical contract runtime and strict JSON reader;
it does not replace the native helper or invent domain judgments. Keep shared
code in Codify, synchronize its standalone release before generating copies,
and publish only after real native/transfer/rejection cases and a fresh compile.
The relative generation manifest describes authored source outputs, while
machine/session execution records stay in `.tkstack/`.

## 4. Validate the result

```sh
python3 <skillify-directory>/scripts/skillify.py check /repo/skills/inspect-contracts --require-tool
```

The helper validates a documented [portable profile](../references/validation.md):
name/path, required single-line metadata, package license, local inline resource
links, contained resources, and Python syntax without executing scripts. It is
not a general YAML/CommonMark implementation, TypeScript compiler, native graph
builder, or behavioral grader. Run the native tool and check original/transfer
outputs, negative/error cases, repeatability, and relevant concurrency before
claiming successful conversion. For inputs
outside this profile, use a real compatible validator; never rewrite valid
upstream formats merely to satisfy this helper.

Exercise objectively verifiable helpers and public outcomes with a reproducing
case, distinct transfer case, and negative/boundary case. Include retries,
concurrent ownership, and failure behavior when relevant. Test triggering with
both should-select and should-not-select prompts if making trigger claims.
Structural checks alone do not establish skill effectiveness or model gains.
For subjective output, inspect actual artifacts against the brief; don't add a
meaningless keyword/test-count proxy just to manufacture a score.

Use the existing `learn improve`/SkillOpt adoption process for automatic revision
search when real adapters and held-out cases are available. An explicit feature
request can use appropriate engineering tests without pretending a model trial
ran. `hill-climb` can manage a bounded genuine eval; it does not replace missing
task evidence. Apply `unslop` to the result when available.

## 5. Install and deliver within scope

For this dotfiles repository, add a new distributable package to the marketplace,
refresh inventory/routing, run the offline installer, and verify its actual links
and native requirements. Existing entries should be updated rather than duplicated.
For another repository, use its established installation route and preserve
unrelated configuration. A package being present is different from a harness
having loaded it; report actual tests and native smoke-test limits.

Keep changes incremental and reviewable. An explicitly active `sdlc` workflow
owns BDD/contracts, isolated task graphs, evidence, and stacked PR delivery.
Authoring a skill alone does not request publication or unrelated merges.

Finish with package paths, the procedure captured, provenance where useful,
actual validation, installation state, and remaining gaps. Resume any original
task after capturing its reusable procedure.
