# Learning from corrections

Invoke `/learn` in a slash-command harness or `$learn` in Codex. The skill also
matches user corrections and expressed frustration automatically. Its job is
to change the reasoning that produced the mistake, then apply that change to
the work already underway.

The data and helper have no harness API dependency. Every supported harness
reads the same store; another AGENTS.md-aware harness can follow the same
pointer without migrating the evidence.

## Subcommands and help

Use `/learn help` (or `$learn help` in Codex) to discover commands, or
`/learn help <name>` for focused guidance. Directly select `skillify`, `hookify`,
`instructify`, `flowify`, `lintify`, `reusify`, or `codify` as a Learn subcommand:

```text
/learn help reusify
/learn reusify init src --preview
/learn skillify package our contract-review procedure as a reusable tool
/learn lintify enforce the stated invariant with our existing CLI linter
/learn codify compile docs/release.md into scripts/release.lock.json
```

Learn preserves the request, nested commands, parameters, evidence, and scope,
then follows the named skill's index and actual tools. Preview/audit intent
keeps the entire handoff read-only. Help and missing payloads show guidance
without capturing feedback or reviewing sessions. A direct route does not
start a full consolidation sweep. Missing sibling skills are reported as
explicit dependencies; a standalone Learn package still provides their help.
See the [bundled command contract](../skills/learn/references/subcommands.md).

The Python helper also supports `help [topic]`; no command prints help and
exits successfully without initializing state:

```sh
python3 skills/learn/scripts/learn.py help
python3 skills/learn/scripts/learn.py help reusify
python3 skills/learn/scripts/learn.py help sessions
```

Native helper commands manage records/sessions. Direct ___ify execution is
an agent skill workflow. Bare `/learn` retains its ordinary learning and
consolidation behavior; `-h`/`--help` retain standard CLI usage.

## The three layers

| Layer | File | Purpose |
| --- | --- | --- |
| Evidence | `.tkstack/steering/events.jsonl` | Exact user corrections, their provenance, and the decision being corrected; also rule lifecycle events |
| Procedural evidence | `.tkstack/steering/experiences/<id>.md` | Derived task/tool observations and candidate skill lessons, separate from user authority and active steering |
| Knowledge | `.tkstack/steering/patterns/<rule-id>.md` | The mistaken assumption, reasoning principle, corrective action, scope, transfer case, and boundary case |
| Active steering | `.tkstack/steering/rules.md` | Compact accepted rules loaded at task start; no raw transcript history |

The agent performs the abstraction. The Python helper validates records,
preserves evidence, prevents duplicate replay, and compiles deterministic
views. It does not claim to infer a sound reasoning rule from a keyword or
silently call an external model.

For example, “No. Not later. Do it all now.” was captured with the surrounding
scope decision. The active lesson is to use the user's current authorized
scope as the completion criterion, while respecting real access requirements
and newer instructions. It transfers to other multi-part tasks rather than
becoming a brittle rule about one package.

## Capture and promotion

Capture every correction and expressed frustration visible to the agent,
including observations whose remedy is not yet clear. Retain the user's words
and label provenance accurately. Replaying the same message deduplicates;
another message expressing the same correction reinforces its evidence.
Unavailable transcript history is not invented. Credentials are redacted
before recording.

A clear explicit correction can produce an active rule in the narrowest
supported scope. An uncertain interpretation remains a candidate outside
startup steering. A reversal explicitly supersedes or retires the old rule,
preserving why both decisions existed. Reinforcing a rule retains all its
earlier evidence. A silent change from repository-specific to personal policy
is rejected by the helper.

Rules are scoped to the person, a named repository, or a named task. Each
contains a trigger, mistaken assumption, reasoning principle, concrete action,
boundary, transfer case, and counterexample. A task reminder or a personality
judgment is not a reasoning principle.

## Harness adapters

The installer links `.agents/steering` back to this checkout's `.tkstack/steering/`.
It preserves existing instructions and maintains only its marked block:

| Installation | Codex | Claude Code | Cursor |
| --- | --- | --- | --- |
| Project | `AGENTS.md` | `CLAUDE.md` | `.cursor/rules/tkstack-steering.mdc` |
| Home | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` | `~/.cursor/rules/tkstack-steering.mdc` |

The pointers require reading matching active rules at task start and after a
correction, then capturing new evidence with `learn`. This is instruction-based
capture by the active agent, not a claim that a background service can read
every harness's private transcript database. Current explicit instructions
and higher-priority rules take precedence over older learned preferences.

Use `--scope home` with a custom home-like target. Otherwise a target equal to
the actual home is a home installation, and other targets are project installs.
Uninstall removes this checkout's pointers and links, retaining the shared
evidence store and unrelated instructions.

## Inspect and check

```sh
python3 skills/learn/scripts/learn.py show
python3 skills/learn/scripts/learn.py show --json
python3 skills/learn/scripts/learn.py check
python3 skills/learn/scripts/learn.py render
```

Use `--store <directory>` before the command, or set
`TKSTACK_STEERING_DIR`, to select a different store. Input formats are in the
skill's `references/records.md`. Capture and rule updates use a filesystem lock;
the ledger is append-only during normal operation. Derived views can be rebuilt
from it, and malformed evidence is reported rather than silently discarded.

The initial store contains two actual user observations from this setup
conversation and two active rules. Future evidence accumulates in the same
format across harnesses.

## Skill improvement and report-only audits

The root `skills/learn` package is now version 0.6.0, with a concise entrypoint
and conditional operating/structural-learning references. Its original correction
capture remains automatic when feedback matches. An explicit `/learn improve
<skill>` request adds a procedural review: identify the reusable lesson from
actual task evidence, choose the smallest owned target, preserve the baseline
and proposed diff, and validate a reproducing case, transfer case, and boundary.
The package includes an [improvement workflow](../skills/learn/references/improvement.md)
and [proposal template](../skills/learn/templates/improvement.json).

Task and tool outcomes use `learn.py experience --input <file>`. They append
typed `experience` events and render explanatory pages without entering the
user-correction collection or `rules.md`. They cannot supply the required user
evidence for an active rule. The JSON interchange adds `experiences` while
retaining `corrections` and `rules`. The helper records and checks data; the
agent still judges whether a proposed lesson is sound.

`/learn report` and `/learn audit` are read-only agent modes. They can inspect
available instructions, skills, plugin/MCP configuration, and actual usage
artifacts, while stating the observation window and gaps. They do not change
the store, rewrite skills, retire rules, or disable integrations. Absence of
an observed invocation is not proof that an integration is unused.

For automatic revision search, keep the selected SkillOpt gate. Explicit feature
implementation is assessed through its actual behavioral checks; do not label
that engineering work a measured gain in model quality. See
[Grok source findings](grok-learn.md) for the upstream investigation and the
read-only `learn.py locate-grok` helper. The portable implementation was not
copied from an unavailable runtime prompt.

## WikiSkill's role

The installed WikiSkill implementation is
[`ashutoshsinghpr7/wikiskill`](https://github.com/ashutoshsinghpr7/wikiskill), an
independent MIT-licensed implementation of the WikiSkill paper. Its 0.1.5 CLI
runs from the pinned Python source without package downloads. An isolated
workspace at `.tkstack/wikiskill` uses its Codex backend and includes upstream
demo tasks. No inference, skill evolution, or paid training has been run.

`learn show --json` is the provider-neutral interchange snapshot. A WikiSkill
or another evaluator can use the evidence to propose candidates and compare
them against held-out tasks. Keep evaluation traces and private wikis outside
startup context, and preserve evidence IDs in accepted changes. Rule examples
check clarity; they do not establish a measured improvement in model behavior.
The steering system works without WikiSkill, a daemon, or a model-specific
memory store.

After comparing SkillOpt, WikiSkill, Vally, and Waza, the selected revision
engine for the custom `learn` and `sdlc` packages is SkillOpt-Sleep. The
[`scripts/evolve.py`](../scripts/evolve.py) driver keeps evidence and steering
unchanged, turns off project-memory edits, and stages only skill proposals
behind strict improvement and per-task no-regression gates. See
[the comparison and initial trial](skill-evolution.md). WikiSkill remains
installed for its evidence/knowledge organization and optional future tasks.

For a standalone marketplace installation, the helper defaults to the working
project's `.tkstack/steering/` when no explicit or existing shared store exists.
It searches the active repository and configured aliases without a home fallback. Initialize an empty store
with `learn.py render`; user data stays outside the installed plugin cache.
The dotfiles installer additionally supplies startup pointers across harnesses.

Local histories and derived session views are retained under `.tkstack/steering/`
and ignored by Git. Fresh clones initialize empty local records; packaged
standards and anti-slop seeds remain source-authored. See [storage](state-layout.md).

## Scoped storage and session consolidation

`.tkstack` has workspace, user, and global roots, configured through
TKSTACK_WORKSPACE_DIR, TKSTACK_USER_DIR, and TKSTACK_GLOBAL_DIR. Defaults are
`<workspace>/.tkstack`, `~/.tkstack`, and `/etc/.tkstack`. Explicit writes never
fall back across scopes. `learn show --all-scopes` loads curated rules in nearest
scope order; the nearest same-ID rule shadows broader records. See
[storage conventions](state-layout.md).

Temporary records live in `sessions/<session>/`, are gitignored, and can be
reviewed independently of the harness. An invoked `/learn` or focused
`/learn consolidate [session]` reviews that evidence, abstracts transferable
reasoning, and applies the smallest useful set of `instructify`, `reusify`,
`skillify`, `codify`, `flowify`, `lintify`, and `hookify`. Normal automatic
correction capture remains narrow; reports/audits remain read-only.

The helper provides session start/close/list, bounded review snapshots, and
hash-bound semantic-decision plans. Code validates/routes the decisions; the
agent performs actual abstraction and the selected skills' authoring work.
Useful evidence, decisions, and promotion receipts stay outside temporary
sessions under ignored `learnings/`; generalized artifacts stay at their
canonical source paths. No automatic TTL, deletion, background transcript mining,
or arbitrary session-command execution is installed. See the
[full consolidation procedure](../skills/learn/references/session-consolidation.md).
