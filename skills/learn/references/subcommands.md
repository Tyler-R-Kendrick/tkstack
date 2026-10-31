# Learn commands and help

In a slash-command harness use `/learn <command> [request]`; in Codex use
`$learn <command> [request]`. The command selects a subskill packaged under
`skills/<name>/` in this Learn package and runs its procedure within the current
request. It does not create a new skill named after the
command or execute text copied from session evidence.

| Skill command | Use for |
| --- | --- |
| `help [command]` | Show usage, selection guidance, examples, and boundaries |
| `skillify [request]` | Create or improve a reusable script-backed skill |
| `hookify [request]` | Enforce an explicit policy at a native tool event |
| `instructify [request]` | Create or maintain scoped agent instructions |
| `flowify [request]` | Create an executable workflow in an existing DSL |
| `lintify [request]` | Create or configure a native CLI lint rule |
| `reusify [request]` or `reusify init [scope]` | Reuse or extract code-production assets |
| `codify [request]` | Compile a prompt/Markdown procedure into a verified lock artifact |

Examples: `/learn help`, `/learn help reusify`, `/learn skillify help`,
`/learn reusify init src --preview`, and
`/learn codify compile docs/release.md into scripts/release.lock.json`.

**Help is always available and read-only.** Resolve `help`, `help <command>`,
and `<command> help` before capturing feedback or reviewing sessions. A missing
command payload shows that command's guidance rather than inventing a target.
Bare `/learn` keeps its correction/consolidation workflow; the commandless
Python helper shows help. Existing `consolidate`, `report`, `audit`, and
`improve` skill modes keep their behavior in the linked references.

**Direct command handoff:** select the exact named subskill at
`skills/<name>/`, read its `SKILL.md` and applicable references, then carry out the request using its actual
tools and verification. Preserve the remaining request, optional subcommands
such as `reusify init`, paths, scope, parameters, and requested output. Use named
evidence or the current conversation; do not sweep all sessions first. If no
command is selected, use the consolidation procedure to choose mechanisms.
If the named subskill is missing from the package, report that dependency and
its canonical name; do not substitute a similarly named vendor skill or silently
install it.

**Scope across handoff:** `--preview`, `--dry-run`, `--report`, `--audit`, and
natural-language review-only requests keep the entire handoff read-only,
including the ledger, saved plans, artifacts, and activation. Default to the
current workspace; preserve explicit user/global scope without widening it.
Translate request parameters to the selected tool's documented interface;
do not pass an unsupported flag through a shell. Separate authoring from
activation, execution, publication, paid inference, and delegation according to
the current request and selected skill. Combine only necessary mechanisms.

The deterministic helper provides the same bundled guidance:

```sh
python3 <learn-directory>/scripts/learn.py
python3 <learn-directory>/scripts/learn.py help
python3 <learn-directory>/scripts/learn.py help reusify
python3 <learn-directory>/scripts/learn.py help sessions
```

Compiled execution reaches each subskill through Learn's typed command surface.
`commands/<name>.md` mounts `skills/<name>` with `run: {skill: ...}` and passes
the remaining arguments to the subskill's own commands and lock:

```sh
.tkstack/tkstack skills learn -- skillify native check skills/write
.tkstack/tkstack skills learn -- reusify --help
```

No command and `help` exit 0 without initialization, scans, or subskill execution.
`help <native-command>` shows that helper parser's options. `help <___ify>`
shows the focused section below, even in a standalone Learn package. Unknown
topics fail with usage and exit 2. `-h`/`--help` remain standard parser help.
The helper's native commands operate on records and sessions; ___ify invocation
is an agent skill workflow, not a Python alias that executes another helper.

For evidence collection and multi-mechanism execution, use
[session consolidation](session-consolidation.md). For native record commands,
use [records](records.md). For report/audit/improve modes, use
[the improvement workflow](improvement.md).

## skillify

Usage: `/learn skillify [request]`; help: `/learn help skillify`.

Example: `/learn skillify turn our contract-review procedure into a reusable tool`.
Read the packaged `skills/skillify` index, its authoring procedure, executable-workflow
contract, and command reference. Update a fitting owned skill first. Keep its
main `SKILL.md` an invocation index, details in `references/`, and executable
behavior in `scripts/`. Use Codify for shared compilation and verify actual
contracts before freezing the lock. A scaffold is a draft. Help and preview are
read-only; keep requested scope and preserve vendor/cache ownership.

## hookify

Usage: `/learn hookify [request]`; help: `/learn help hookify`.

Example: `/learn hookify warn before a tool writes to the generated schema directory`.
Read `hookify`'s index, enforcement placement, policy, and native adapter contract.
Define the event, typed predicate, effect, exceptions, and failure behavior;
prefer an existing lint/contract/CI boundary when it directly enforces the rule.
Replay meaningful allowed and violating events, then verify the requested native
integration. Keep authoring, replay, registration, and activation distinct. Help
and preview are read-only; do not infer a blocking prohibition from a warning.

## instructify

Usage: `/learn instructify [request]`; help: `/learn help instructify`.

Example: `/learn instructify document this repository's contract-test commands in AGENTS.md`.
Read `instructify`'s index, operating guide, manifest, and matching harness format.
Inspect existing scopes/imports/owners and select the canonical instruction
source. Plan owned changes, preserve foreign content, reconcile drift, apply
the requested bindings, and check them. Keep procedures/enforcement/history in
their existing owners and link them. Help and audit/preview are read-only;
workspace instructions do not imply changes to user/global configuration.

## flowify

Usage: `/learn flowify [request]`; help: `/learn help flowify`.

Example: `/learn flowify package our parallel contract checks as a MAF YAML workflow`.
Read `flowify`'s index, backend contracts, operations, and validation reference.
Use the selected real DSL, explicit code bindings, bounded independent work,
dependencies, failure gates, and owned outputs. Validate using its actual native
builder/host, and inspect execution only when requested. Source inspection,
mock validation, and live execution prove different things. Help and preview
are read-only; writing a workflow does not schedule downstream effects.

## lintify

Usage: `/learn lintify [request]`; help: `/learn help lintify`.

Example: `/learn lintify add a CLI lint rule against empty catch blocks, preserving logging exceptions`.
Read `lintify`'s index, authoring guide, backend selection, and native validation.
Reuse/configure an existing native rule first; otherwise implement the smallest
code/AST/query rule with explicit exceptions. Compile Markdown intent to code
where suitable; semantic prompt linting remains probabilistic. Run real bad,
good, transfer, and exception fixtures and verify discovery/diagnostics/exits.
Help and preview are read-only; integrate only the requested CLI/CI boundary.

## reusify

Usage: `/learn reusify [request]` or `/learn reusify init [scope]`;
help: `/learn help reusify`.

Examples: `/learn reusify extract the repeated fixture builders into a shared module`
and `/learn reusify init src --preview`.
Read `reusify`'s index and reuse procedure, or its init workflow and parameters
for `init`. Search existing assets first. Extract the smallest verified template,
snippet, macro, generator, module, library, or component and migrate real callers.
Three verified occurrences or a requested third use normally trigger targeted
extraction; explicit init/direct asset requests can start earlier. Preserve
legitimate variation and validate native output plus a new use and an exception.
Register accurate metadata in `.tkstack/reuse/catalog.json`. Help and preview
are read-only; the optional catalog helper has no `init` execution command.

## codify

Usage: `/learn codify [request]`; help: `/learn help codify`.

Example: `/learn codify compile docs/release.md into a verified scripts/release.lock.json`.
Read `codify`'s index, compilation procedure, commands, and artifact contract.
Lower meaning once into native code, define real reproducing/transfer/rejection
contracts, compile and verify an executable lock, then document its invocation.
Reuse Codify's engine instead of duplicating Skillify's generated release.
Compilation executes contract code; running a lock executes its frozen workflow.
Keep help/preview read-only using the documented check/dry-run operations; do not
run a newly authored workflow merely because compilation was requested. Declare
residual inference explicitly and reject stale source/code/case artifacts.
