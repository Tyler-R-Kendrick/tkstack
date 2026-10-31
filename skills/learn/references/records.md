# Records and commands

The helper uses Python's standard library. Run `learn.py --help` for commands.
Global `--store <directory>` goes before the subcommand. `--input -` reads JSON
from stdin; a file avoids shell quoting problems with exact user text.

No command or `help` prints read-only help and exits 0. Use `help <command>`
for native parser usage or `help <___ify>` for the bundled skill guidance.
These paths resolve before state discovery and never initialize the ledger.
See [skill subcommands and help](subcommands.md) for agent invocation forms.

## Capture an observation

```json
{
  "source": {
    "conversation": "project setup session",
    "message": "user reply after the partial installation summary"
  },
  "user_text": "No. Not later. Do it all now.",
  "context": "The assistant installed one requested package and deferred the others.",
  "kind": "correction",
  "failure": "The agent narrowed the current authorized scope when declaring completion."
}
```

`kind` is `correction`, `frustration`, or an explicit `preference`. A preference
records a desired standard without asserting an assistant mistake occurred.
If one message expresses both correction and frustration, one
record can preserve both in its context rather than duplicating the quote.
`source.conversation` and `source.message` are required. Descriptive labels
are explicitly provenance labels, not fabricated provider-issued IDs.

The evidence ID hashes its provenance and quote. The same source and quote
deduplicate; a repeated quote in a new message is additional evidence.

## Write a reasoning rule

```json
{
  "id": "complete-authorized-scope",
  "status": "active",
  "scope": {"kind": "personal", "value": "*"},
  "trigger": "Deciding whether an authorized task is complete",
  "assumption": "A useful subset is enough to declare completion",
  "principle": "Use the user's current authorized scope as the completion criterion",
  "action": "Complete feasible authorized work before returning; name any concrete blocker and the remaining scope",
  "boundary": "Respect real access requirements, missing required inputs, and newer scope changes",
  "transfer": "A request for several integrations includes their configuration and verification, not just the first package",
  "counterexample": "An unavailable account login is a blocker to report accurately, not permission to claim a working connection",
  "evidence": ["correction-id-returned-by-capture"]
}
```

All reasoning fields, scope, and at least one valid evidence ID are required.
Status defaults to `candidate`; `active` is an explicit decision. A revised rule
retains prior evidence. Optional `supersedes` lists obsolete rule IDs. A change
to a rule's scope must replace the old rule explicitly rather than silently
extending it.

## Inspect and maintain

```sh
python3 <skill-directory>/scripts/learn.py show
python3 <skill-directory>/scripts/learn.py show --json
python3 <skill-directory>/scripts/learn.py render
python3 <skill-directory>/scripts/learn.py check
python3 <skill-directory>/scripts/learn.py retire complete-authorized-scope --reason "Replaced by a newer preference"
```

`events.jsonl` is the source of truth. Normal commands append observations and
rule changes; they do not rewrite historical evidence. `rules.md` and pattern
pages are derived views. Regenerate them after reconciling an edited ledger.
Concurrent writers use a short filesystem lock and fail clearly if it is busy;
retry after the writer finishes. After an interrupted process, remove a stale
lock only after checking that its writer is no longer running.

## Capture procedural experience

`experience` records a real task/tool observation and a candidate procedural
lesson, independently of the user-correction evidence accepted by `rule`:

```json
{
  "source": {
    "kind": "tool",
    "conversation": "actual workflow or run label",
    "message": "actual tool result or artifact label"
  },
  "target_skill": "example",
  "result": "failure",
  "observation": "The executed command failed for the recorded dependency mismatch; retain its actual command, output, and artifact references here.",
  "lesson": "Candidate procedure: verify the declared dependency boundary before retrying the command."
}
```

Run `learn.py experience --input <file>`. `source.kind` is `task` or `tool`;
the result is `success`, `failure`, or `mixed`. All fields shown are required.
Source labels describe actual provenance; they are not fabricated provider IDs.
Use a real artifact/reference in the observation when one exists. The helper
checks record shape and integrity; it cannot authenticate a claimed tool run.

The helper appends an `experience` ledger event, assigns a deterministic ID,
and renders `experiences/<id>.md`. Replaying the same record deduplicates.
Experiences stay out of `rules.md` and cannot satisfy a rule's required **user**
evidence. The additive `experiences` field in `show --json` preserves the old
`corrections` and `rules` fields. Do not enter the illustrative record as a
real observation.

## Locate a Grok skill body

```sh
python3 <skill-directory>/scripts/learn.py locate-grok
python3 <skill-directory>/scripts/learn.py locate-grok --grok-home /path/to/grok-home
```

This command only inspects known `learn` paths and the bundle manifest inside
the selected Grok home. It reports scope, path, SHA-256 and any cached manifest
match; it does not print the skill body, read credentials, contact xAI, run
Grok, or initialize a steering store. See [the source findings](grok-build.md).

## Skill improvement reports

`/learn report`, `/learn audit`, and `/learn improve` are agent workflow modes,
not similarly named Python subcommands. Follow `references/improvement.md` and
the proposal template from the skill root. Keep candidate files and diffs
outside active steering; a report-only request causes no writes. No helper
automatically rewrites a live skill or disables an integration.

## WikiSkill interoperability

Keep WikiSkill training traces and private wikis separate from startup steering.
The `show --json` snapshot exposes corrections and rules without a harness API.
An evaluator can consume that snapshot, retain evidence IDs, and propose a
candidate rule or personal skill. Promote an inference after user confirmation
or a real validation result; record the basis in the rule's action/context.
Examples in a rule are not a substitute for held-out evaluation scores.

## Scoped stores and session commands

Global flags precede the command. `--scope workspace|user|global` selects an
explicit store. `--project` selects an exact workspace; it cannot select user or
global scope. `--store` cannot be combined with those discovery flags. Existing
TKSTACK_STEERING_DIR and installed shared aliases remain supported for ordinary
unscoped capture. No missing/permission fallback writes to another root.

```sh
python3 <skill-directory>/scripts/learn.py show --all-scopes
python3 <skill-directory>/scripts/learn.py --scope user show
python3 <skill-directory>/scripts/learn.py --project /repo sessions list
python3 <skill-directory>/scripts/learn.py sessions review --session actual-id
```

`show --all-scopes` returns curated rules by layer and effective active rules,
with the nearest same-ID record shadowing broader records. It does not create
stores or copy evidence across scopes. `sessions start/close` write only their
selected session; `list`, unsaved `review`, and unsaved `plan` are read-only.
`review --save`/`plan --save` explicitly preserve ignored records outside the
session in `learnings/reviews/`. They do not execute another skill.
See [session commands and decision protocol](session-consolidation.md).
