# Compatibility evaluation

This report covers the initial four packages evaluated on 2026-10-29. See
`docs/integrations.md` for the additions and their current runtime readiness,
and `docs/learning.md` for the shared steering system.

The four initial collections are installed and their
source revisions are pinned. Pstack is the preferred engineering entry point;
Tstack adds PR lifecycle workflows, and Matt Pocock adds spec, design,
implementation, and productivity workflows. Cursor Team Kit supplies the
companion skills Pstack references.

## Installed sources

| Source | Pinned revision | Skills | Snapshot files |
| --- | --- | ---: | ---: |
| Pstack 0.9.0 | `74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12` | 34 | 85 |
| Cursor Team Kit 1.2.0 | `74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12` | 18 | 29 |
| Tstack | `1085050f3baed1ac724caa4a8166145fb2ac88af` | 9 | 16 |
| Matt Pocock 1.3.2 | `a496f5513d4a4cf889bc48e189e579f4b0bdf6aa` | 38 | 176 |

The 306 source files retain their licenses, byte contents, executable modes,
and symlink targets. Matt's collection includes the 27 promoted skills, four
misc skills, and all seven beta skills currently present upstream. Beta skills
can change or disappear upstream; their pinned versions remain reproducible.

## Findings and decisions

### Pstack and Cursor Team Kit

Pstack provides 14 workflow/reference skills and 20 engineering principles.
Its most useful default is `poteto-mode`; `architect`, `how`, `why`, and
`interrogate` supply the deeper design and investigation paths. These are a
strong fit for the requested Pstack-focused baseline.

Pstack explicitly calls `deslop`, `control-cli`, and `control-ui`, which are
shipped separately in Cursor Team Kit. That entire companion package is now
installed, including its two agents and two Cursor rules. Cursor itself
supplies built-ins such as `babysit`, `create-skill`, and `/loop`; copying skill
files does not supply those built-ins in other harnesses.

`setup-pstack` targets Cursor's per-role model rule and requires actual entitled
model slugs. No model IDs were fabricated. Its multi-model panels require the
native model/delegation features of the active harness. The shipped Markdown
agents are registered by filesystem links in Claude Code and Cursor, not
translated into native Codex agent configuration.

### Tstack

All nine skills are installed together, so the dependency chains from
`full-send`, `full-stop`, and `takeover` are present. `file-pr`, `babysit-pr`,
`modernize`, and `leaving-pr-comments` provide the reusable PR building blocks.

`council` requires models from three providers. `sol-loop` specifically requires
Sol and explicitly rejects silently substituting another model. T3 Code can
supply these through its delegation tools; other harnesses need an equivalent
model route. `full-send` merges after its gates and is invoked explicitly;
`full-stop` reaches the gate without merging. Installation invoked neither.

The PR watcher needs Python and an authenticated GitHub CLI. It uses POSIX file
locking, so the shell helpers target Linux/macOS rather than native Windows.

### Matt Pocock

The skills are nested inside engineering, productivity, misc, and in-progress
buckets. The installer now discovers all of them recursively; it does not
mistake a bucket README or an `agents/openai.yaml` file for a separate skill.
Codex invocation-policy metadata and all supporting templates are retained.

Matt's `tdd` collides with Pstack's `tdd`. Pstack keeps the original name, and
Matt's skill is installed as `matt-tdd`. Matt's generated skill tree rewrites
its declaration and skill calls, including the calls from `implement`,
`implement-spec`, and `ask-matt`. Relative file links such as `../tdd/SKILL.md`
still point to the original directory shape inside the generated view. No
upstream bytes are modified.

The engineering workflows expect project context: an issue tracker, triage
labels, and domain documentation. This repository has those settings under
`docs/agents/`, plus `GLOSSARY.md`, `SCOPE.md`, `docs/standards.md`, and an ADR.
GitHub's label inventory was not changed as part of installing local files.

The four misc skills are setup tools, not automatically executed installers:
installing `git-guardrails-claude-code` does not turn on a Git hook, and
installing `setup-pre-commit` does not add Husky to unrelated projects.
The beta `claude-handoff` needs Claude's background-agent CLI; other beta skills
may require scheduling or project-specific TypeScript tooling.

## Verification performed

- Verified the complete 306-file source inventories and Git blob hashes,
  executable modes, and the upstream `AGENTS.md` symlink.
- Checked all 99 installed skill declarations against their unique installed
  names and preserved their supporting files.
- Verified the 305 managed links: 99 skills per harness, three agents each in
  Claude Code and Cursor, and two Cursor rules.
- Exercised fresh-checkout installation, dry-run behavior, repeated installation,
  collision handling, alias routing, relative references, and selective removal
  in the automated installer tests.
- Checked shell/Python syntax for seven bundled helper scripts and JavaScript
  syntax for Cursor Team Kit's PR canvas renderer.
- Ran Pstack's decision logger against a temporary TSV, including its formula
  escaping; ran Tstack's PR watcher help; and ran Matt's Git guardrail against
  allowed and blocked command strings without executing those commands.
- Reviewed local Markdown-link checks. The two unresolved Matt links are
  upstream examples: a ticket placeholder in `wayfinder` and a target-project
  README to be created by `setup-ts-deep-modules`.

## Runtime limits of this evaluation

These are installation and source-compatibility results. They do not measure
the quality, speed, or cost of a model following the workflows. This environment
has Codex, Python, Bash, Node, jq, and an authenticated GitHub CLI; it does not
have Cursor or Claude Code CLIs. Native Cursor/Claude execution and cross-provider
model panels were not exercised. No PR was created or merged to test a workflow.
Model access, browser tooling, and target-project dependencies remain properties
of the harness and project using the installed skills.

Run `python3 scripts/doctor.py --target .` to verify this checkout's current
installation without changing it.
