# Run skills and workflows from `.tkstack`

Use the destination’s `.tkstack/tkstack` launcher or the source program below. From any repository, `~/.tkstack/tkstack status` checks its project installation or your personal baseline.

```sh
python3 src/tkstack.py help
python3 src/tkstack.py list skills
python3 src/tkstack.py list workflows
python3 src/tkstack.py workflows normalize-labels -- labels normalize -l '[" b ","a","a"]'
python3 src/tkstack.py skills my-skill -- command --flag value
python3 src/tkstack.py skills my-skill --call /path/to/tool-call.json
python3 src/tkstack.py tools skills my-skill --format responses
python3 src/tkstack.py check skills my-skill
```

`normalize-labels` is a registered working workflow and returns
`{"labels":["a","b"]}`. `my-skill` illustrates a user-authored compiled package;
it is not a preinstalled name. Singular `skill`/`workflow` aliases are supported.
Use `--project /repo` **before** the operation to select an exact workspace.
Without that option, the shared scope helper honors TKSTACK_WORKSPACE_DIR and
active repository discovery. A user/global launcher therefore uses the current
workspace instead of binding execution to the dotfiles checkout.

## Execution contract

The installed launcher uses the source checkout’s managed Python when present. Provision its locked command dependencies once per checkout before using typed skills or the project constraint hook. From the source checkout, run:

```sh
python3 -m venv .tkstack/runtime/command-schema
.tkstack/runtime/command-schema/bin/python -m pip install --require-hashes -r skills/learn/skills/codify/requirements/requirements.lock
```

Projects sharing that checkout use the same interpreter even when a Git client starts with a different PATH. [Project adoption](bootstrap.md#adopt-team-constraints).

Package commands use Codify's exact `commands/*.md` schema and dispatcher:
OpenAI function-tool parameters, local nested paths/aliases/flags/defaults,
and a verified artifact binding. CLI and Responses/Chat tool calls share input
validation. Execution checks freshness and the exact command-to-lock binding,
then runs frozen code in an isolated temporary session with a bounded deadline.
`--timeout 1..300` defaults to 30 seconds for ordinary commands. A reviewed,
lock-bound command may declare a longer default and maximum, up to 86,400
seconds; an explicit `--timeout` can select a shorter limit. Long-running
commands receive SIGTERM before forced termination on POSIX, so a cooperating
controller can stop its own child sessions. A hard kill or host crash cannot
guarantee descendant cleanup. An extended-timeout command requires its own
process group and fails explicitly inside another compiled workflow. Workflow
exits and output propagate. POSIX commands require `waitid(WNOWAIT)` and the
default SIGCHLD disposition; embedding hosts must not reap their children.
Lost child ownership stops execution without signaling the former process ID;
descendants may survive and require external process reconciliation.

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

Source defaults come from `src/runner.json` plus the installer's canonical
skill catalog, preserving owned/upstream aliases. Packaged subskills, such as
Learn's ___ify skills, also register under their own names, so
`.tkstack/tkstack skills codify -- help` and
`.tkstack/tkstack skills learn -- codify help` reach the same package and lock.
Harness installation still links only the parent. Each scoped `.tkstack` root
can add `runner.json` with version 1 and optional `skills`, `workflows`, and `dependencies` fields:

```json
{
  "version": 1,
  "skills": {"my-skill": "../skills/my-skill"},
  "workflows": {"release": "../workflows/release"},
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

## Model and execution boundary

The invoking agent supplies all semantic judgment in its current conversation,
model and harness. The runner does not offer a provider, model or agent-harness
selection. Legacy locks declaring separate inference are rejected before
execution. No-inference declarations are not an OS sandbox: execute only
trusted code and use the host's actual isolation controls where needed.

`--dependencies` reuses preinstalled Node dependencies for supported
deterministic workflows. The runner performs no downloads. Child processes use
the selected workspace and retain the user's ordinary environment.

## Run it

`python3 src/tkstack.py` is the runner. `install.sh` does not publish a copy
of it and does not create `/etc/.tkstack`. Pass `--project /repo` before the
operation when the workspace is not the current directory. Help, list, tools,
and check are read-only.

Compiled execution defaults to a 30-second outer deadline; use `--timeout`
when a different bounded workload requires it. For executed operations the
runner appends a local `.tkstack/runs/timing/operations.jsonl` record with elapsed
monotonic time, deadline, outcome, artifact identity and basic runtime environment,
without prompts or payloads. This includes compiled model and report verification
operations: even a read-only command creates this local timing record. Built-in
help and version, discovery, and artifact checks do not execute a workflow and
remain read-only. An untrusted payload cannot suppress timing by naming an operation. A trace-write
failure is reported without pretending the operation itself did not happen.
Direct helper execution and MCP calls made by other hosts do not pass through
this runner; configure and verify their deadlines and traces separately. An
outer timeout does not prove a remote request was cancelled.

## Owned normalized skill commands

All owned skills now provide `model`, `verify --report`, and their declared
`native ...` helper bindings, plus shared reserved help/version. The runtime
executes actual frozen Python code. Models/verification constrain report facts,
evidence bytes and coverage; they do not substitute for article/design judgment,
native workflow execution, or domain-specific gates. See
[the full coverage and maintenance contract](normalization.md).
