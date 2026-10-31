# Run skills and workflows from `.tkstack`

After setup, the selected workspace and user state roots contain executable
`tkstack` files. The source checkout also provides `.tkstack/bin/tkstack` for
the generated PATH. The canonical implementation is `scripts/tkstack.py`; the
generated entrypoints stay ignored, alongside a private ownership receipt.
They use the private command interpreter when available and a Python fallback
for discovery. Keep the source checkout because these are managed launchers.

```sh
./.tkstack/tkstack help
./.tkstack/tkstack list skills
./.tkstack/tkstack list workflows
./.tkstack/tkstack workflows normalize-labels -- labels normalize -l '[" b ","a","a"]'
./.tkstack/tkstack skills my-skill -- command --flag value
./.tkstack/tkstack skills my-skill --call /path/to/tool-call.json
./.tkstack/tkstack tools skills my-skill --format responses
./.tkstack/tkstack check skills my-skill
```

`normalize-labels` is a registered working workflow and returns
`{"labels":["a","b"]}`. `my-skill` illustrates a user-authored compiled package;
it is not a preinstalled name. Singular `skill`/`workflow` aliases are supported.
Use `--project /repo` **before** the operation to select an exact workspace.
Without that option, the shared scope helper honors TKSTACK_WORKSPACE_DIR and
active repository discovery. A user/global launcher therefore uses the current
workspace instead of binding execution to the dotfiles checkout.

## Execution contract

Package commands use Codify's exact `commands/*.md` schema and dispatcher:
OpenAI function-tool parameters, local nested paths/aliases/flags/defaults,
and a verified artifact binding. CLI and Responses/Chat tool calls share input
validation. Execution checks freshness and the exact command-to-lock binding,
then runs frozen code in an isolated temporary session with a bounded deadline.
`--timeout 1..300` defaults to 30 seconds. Workflow exits and output propagate.

An explicitly selected compiled file uses the existing Codify JSON interface:

```sh
./.tkstack/tkstack workflows /repo/workflows/release.lock.json --input /path/to/input.json
```

`--input -`/`--call -` read bounded stdin. A direct lock cannot receive command
arguments/tool calls; a command package uses its declared schema instead of raw
input. The runner never interprets a skill's Markdown, generates code, compiles
on demand, installs dependencies, or invokes an agent as a fallback. Skills
without command definitions/compiled artifacts report their actual unavailable
status. Author and compile them explicitly with Skillify/Codify before running.
Existing prose-only skill procedures remain available through their harnesses.
Flowify MAF/Rhai workflows use their real native runtime through a Codify-compiled
binding with the required definitions included. This runner preserves that host
contract rather than inventing another workflow DSL or inferring YAML semantics.

Package help/version use the reserved definitions supplied by Skillify and the
shared command runtime. Omitting the command displays a generated console man
page; `<command> --help` and `help <command>` share its content. Use
`skills sdlc -- help --format man` to export man(1) source or
`skills sdlc -- version` for declared package metadata. They work without an
artifact, model, pager, terminal-width probe, or state writes; custom workflows
cannot claim their reserved names or flags. API help returns the same text/source
in JSON. These package commands are separate from the outer runner's own help.

Help, version, list, tool exports, and artifact checks are read-only. List uses four
bounded readers and stable ordering; readiness describes the observed revision,
not a reservation against later edits. There is no shell-string execution
binding or implicit workflow/indexing/model job at startup.

## Names and scoped registry

Source defaults come from `harnesses/runner.json` plus the installer's canonical
skill catalog, preserving owned/upstream aliases. Packaged subskills, such as
Learn's ___ify skills, also register under their own names, so
`.tkstack/tkstack skills codify -- help` and
`.tkstack/tkstack skills learn -- codify help` reach the same package and lock.
Harness installation still links only the parent. Each scoped `.tkstack` root
can add `runner.json` with version 1 and optional `skills`, `workflows`, `config`,
and `dependencies` fields:

```json
{
  "version": 1,
  "skills": {"my-skill": "../skills/my-skill"},
  "workflows": {"release": "../workflows/release"},
  "config": "profiles.json",
  "dependencies": "runtime/workflow-node/node_modules"
}
```

Paths are explicit, relative to that registry file (absolute paths also work).
They are data, without environment or shell expansion. Separate skill/workflow
namespaces use workspace > user > global > source precedence. At each scope,
explicit registry entries override discovered directories. Discovery includes
scoped `skills/` and `workflows/`; workspace discovery also reads source folders
and installed `.agents` folders. It reads immediate children, bounded to 512 per
folder, and does not mine unrelated session histories. Registries allow at most
256 entries per kind. Duplicate JSON keys and unknown registry fields fail.

Use a registered name or an explicit directory/lock path. A skill must contain
`SKILL.md`; workflows may be command packages or `*.lock.json` files. The runner
does not synthesize a function signature for a bare lock; select its package
for `tools` exports. A manifest path is an explicit code selection: keep normal
review/trust boundaries for the compiled code it names.

## Model, provider, decision, and harness configuration

Pure-code locks ignore ambient model settings and Node caches. Explicit
`--config` on a no-inference lock is rejected, preserving Codify's contract.
For locks declaring inference, use the existing **version 1 Vercel AI SDK**
`providers`/`profiles` format, including language chat/Responses/gateway,
decision, or supported harness profiles. Reuse
[the canonical configuration contract](../skills/learn/skills/codify/references/inference.md).
No second model schema, guessed default model, or provider fallback is added.

Selection order is explicit `--config`, TKSTACK_CONFIG, then workspace/user/global
configuration. At each scope an explicit registry `config` wins over that
root's conventional `profiles.json`; a source default comes after scoped files.
Absent an external config, the runner uses a frozen bundled `profiles.json`.
All declared profiles must exist. It projects the chosen document to those
profiles and their referenced providers, preserving profile/model/provider
values, budgets, and credential environment-variable references. Unrelated
profiles are not handed to a lock that did not declare them.

The same native Vercel AI SDK configuration validator runs at the workflow's
inference boundary. The runner validates the document version/collections and
named profile/provider references before invoking code; it does not claim those
checks replace the SDK's full language/decision/harness validation. Configured
model calls remain inference. CLI dispatch itself requires none, and pure-code
locks execute their declared algorithm without a prompt/agent interpretation.

`--dependencies` explicitly reuses a locked `node_modules`; an optional registry
default applies only to Node locks. Codify checks installed direct package
versions against the frozen package. Preserve the actual lock/dependency setup
from the workflow's authoring instructions. This runner performs no downloads.
Each child receives an independent environment preserving proxy, CA, auth,
and guard variables; its TKSTACK_WORKSPACE_DIR is the selected execution scope.
Runtime configuration is passed through private temporary session files rather
than rewriting source, locks, or user credentials.

## Install and verify

Root `install.sh` provisions the command dependencies and generates the runner
for its source checkout and selected initialization roots. Devcontainer and
Codex setup/startup hooks use that same path. Read-only `--check` verifies the
generated entrypoints as well as the existing installation.

For a separately selected scope, use the explicit installer:

```sh
python3 scripts/runner_install.py --project /repo --dry-run
python3 scripts/runner_install.py --project /repo
python3 scripts/runner_install.py --scope user
python3 scripts/runner_install.py --scope global
python3 scripts/runner_install.py --scope user --check
```

The global command needs the host's normal write permissions; ordinary setup
does not create `/etc/.tkstack`. Preview/check initialize nothing. Publication
preserves foreign/modified files and symlinks, uses an ownership receipt and
atomic file replacement, and serializes cooperating writers with a bounded OS
lock. Process death releases the lock. A crash between executable/receipt writes
fails closed on a later ownership mismatch; preserve and inspect both files
before repairing that mismatch. Repeated successful setup preserves bytes.

## Owned normalized skill commands

All owned skills now provide `model`, `verify --report`, and their declared
`native ...` helper bindings, plus shared reserved help/version. The runtime
executes actual frozen Python code. Models/verification constrain report facts,
evidence bytes and coverage; they do not substitute for article/design judgment,
native workflow execution, or domain-specific gates. See
[the full coverage and maintenance contract](normalization.md).
