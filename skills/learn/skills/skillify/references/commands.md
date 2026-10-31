# Invoke Skillify as a tool

The deterministic packaging tool is `scripts/skillify.py`. The skill supplies
the code-mode authoring context; these commands create/migrate/check concrete
packages. Authoring completes the actual executable behavior after scaffolding.

```sh
python3 <skillify-directory>/scripts/skillify.py scaffold \
  --target /repo/skills/inspect-contracts --name inspect-contracts \
  --description 'Inspect compatibility when asked to review contracts.'
python3 <skillify-directory>/scripts/skillify.py scaffold \
  --target /repo/skills/semantic-classify --name semantic-classify \
  --description 'Classify the explicitly supplied residual state.' --backend ai-sdk
python3 <skillify-directory>/scripts/skillify.py convert /repo/skills/existing --backend ai-sdk --dry-run
python3 <skillify-directory>/scripts/skillify.py convert /repo/skills/existing --backend ai-sdk
python3 <skillify-directory>/scripts/skillify.py check /repo/skills/inspect-contracts --require-tool
python3 <skillify-directory>/scripts/skillify.py check <skillify-directory> --require-tool --entrypoint scripts/skillify.py
```

| Command / parameter | Contract |
| --- | --- |
| `scaffold` | Create an absent owned directory with a tool index, four references, executable workflow/CLI starter, and MIT license. Never replace a target. |
| `--target` | Required explicit destination; its basename must equal `--name`. |
| `--name` | Required lowercase kebab-case skill name, at most 64 characters. |
| `--description` | Required nonempty selection/outcome description, at most 1024 characters. |
| `--backend python\|ai-sdk` | Default `python` for pure-code execution. `ai-sdk` supplies TypeScript, native AI SDK `tool()` export, inference profiles/runtime, and locked dependencies. |
| `convert directory` | Seed migration of an existing owned skill. Preserve exact Markdown as authoring data; install absent execution resources and update its invocation index. Does not infer the algorithm or overwrite helpers. |
| `convert --dry-run` | Read-only concrete file plan and source hash; no writer lock or changes. |
| `check directory` | Read-only structural validation; does not execute helpers, call models, or fetch URLs. |
| `normalize directory --profile contract.json [--dry-run]` | Generate the common model/verify/native command surface from an explicit authored contract. Preserve native helpers and modified generated sources; record relative generation ownership, preserve existing source modes, and leave compilation explicit. Dry-run initializes no state. |
| `check --require-tool` | Also require an executable contained in `scripts/` and reject the starter's known unimplemented workflow. Native execution remains a separate check. |
| `check --entrypoint scripts/<file>` | Select a different existing tool entrypoint; requires `--require-tool`. Otherwise exactly one `scripts/run.py` or `scripts/run.ts` is selected. |
| `--help` | Show the parser's actual supported interface. No implicit default helper command. |

Scaffolding returns `status: draft`; conversion returns `workflow-draft`
(`planned` in preview). Port the actual algorithm, gates, and effects into the
workflow. Complete its tool interface/index and references, then run native
cases and `check --require-tool` before delivering. No-op wrappers and forwarding
the whole Markdown to a model do not complete conversion.
It returns `status: structurally-valid`; real outcome checks remain necessary.
Packaging/plan success exits 0; profile errors, incomplete checks, resource errors, and target
collisions exit 1; argparse usage errors exit 2.

See [validation limits](validation.md) before making a compatibility claim and
[authoring](operating-guide.md) for create/adapt/update/audit scope.

## Compile a completed skill

```sh
python3 <skillify-directory>/scripts/skillify.py compile /repo/skills/my-tool \
  --cases /repo/skills/my-tool/cases.json
python3 <skillify-directory>/scripts/codify_runtime/scripts/codify.py run \
  /repo/skills/my-tool/scripts/workflow.lock.json --input /path/to/input.json
```

`compile` delegates to Codify's generated standalone engine. It requires a
completed structurally valid package and implemented tool. The default
entrypoint is exactly one `scripts/run.py` or `scripts/run.ts`; `--entrypoint`
selects another contained tool. It freezes `references/source-skill.txt` when
conversion preserved the original, otherwise the current `SKILL.md`. The lock
is written under `scripts/`; ordinary runs execute its frozen code.

`--cases` is required: version 1 JSON containing 2–64 unique cases with `id`,
object `input`, integer `exit`, and `output` only for successes. Include a success
and a rejection; rejection emits no success stdout. Compilation executes these
cases in private `.tkstack` run directories. Default concurrency is 4; `--jobs`
accepts 1–16. Successful no-inference cases repeat twice. `--dry-run` only plans.

Use repeated `--profile name` for explicit residual inference and
`--dependencies /path/to/node_modules` for a verified npm-ci installation of
AI SDK dependencies. The full generic CLI also supports timeouts, project state,
additional included resources, and explicit inference configuration. Its
`--help` is authoritative. The default artifact includes the entrypoint's whole
directory, excluding dependencies, state, bytecode, Git, and that lock itself.
Use generic Codify `--include` for additional runtime resources outside it.

After a source/implementation/case change, `check`/`run` fail stale rather than
rebuild or invoke an agent. Compile explicitly. Source checks and contract cases
are bounded evidence, not a proof of semantic equivalence or zero network calls.
The native process executes trusted code with the caller's normal authority.

Compilation forwards explicit `--config`, `--project`, `--timeout`, named profiles, dependencies and jobs to canonical Codify. It does not invent a provider or drop the selected workspace/harness profile.
Normalized packages include their owned templates/resources by default. Use `--include` for an explicit resource set; supplying code without required native assets is not a complete tool.
