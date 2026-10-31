# Lever setup

[GitHub Lever](https://github.com/github/lever) is a Copilot plugin for measured
feedback loops and delivery playbooks. This repository pins version 0.1.0 at
`f859d0aa2be96981157ee0480655c84877e3cd98` in `sources.lock.json`.

The selected snapshot contains all 16 skills and their scripts, text guides,
templates, configuration examples, automation recipes, official plugin manifest,
marketplace manifest, and MIT license: 65 verified files. Gallery images,
rendering assets, and talk slides are omitted; view those in the upstream repo.
All selected upstream bytes and executable modes stay unchanged.

## Installed layouts

The normal installer links the 16 skills into `.agents/skills`, `.claude/skills`,
and `.cursor/skills`. The complete upstream tree stays behind those links, so
sibling skills and `../../docs`, templates, config, and automation references
resolve. This adds 48 links to the main installation. Restart the harness so
it discovers the new skills.

The separate project setup follows Lever's
[documented per-repo installation](../vendor/lever/README.md):

```sh
python3 scripts/setup_lever.py --target . --dry-run
python3 scripts/setup_lever.py --target .
python3 scripts/setup_lever.py --target . --check
```

It creates 16 skill links under `.github/skills` and four support-directory
links under `.github/`: `docs`, `templates`, `config`, and `automations`.
Those generated paths are ignored; fresh clones run setup to recreate them.
The pinned canonical sources remain tracked under `vendor/lever`.

The script creates `.github/lever.yml` from
[`harnesses/copilot/lever.yml`](../harnesses/copilot/lever.yml) only if absent.
Existing settings and foreign links/directories are preserved. A resource-name
collision stops setup before links or dials change. It refuses a parent symlink
that would redirect writes outside the selected project.

Remove only owned Copilot links with:

```sh
python3 scripts/setup_lever.py --target . --uninstall
```

Repository dials and unrelated skills are retained. Remove the main three
harness installations through the normal installer and its harness selection.

## Current repository defaults

[`.github/lever.yml`](../.github/lever.yml) sets:

- L2 fallback autonomy when no explicit instruction says who lands the work.
- `high` spend, matching upstream's default, with premium judgment for
  diagnosis, planning, and risky review.
- At most four experiment arms, 75 GitHub API calls per merged PR, and a
  four-minute minimum polling interval.
- America/Chicago status timestamps and quiet unchanged updates.

There is no repository cap or standing merge grant in this template. Lever's
requested level comes from the latest explicit operator instruction, personal
dial, or kickoff. Its effective level still respects actual repository and
GitHub rules. A later explicit "then merge" request can supply the requested
level without an invented confirmation checkpoint.

No personal home config was written. Existing `~/.copilot/lever.yml` settings
continue to take part in upstream's normal resolution. These defaults are
instruction-based dials; the local file is not an independently enforced API
permission or billing system. Unattended work needs the finite budget and stop
conditions required by its selected playbook.

## Start using it

In a slash-command harness, try a read-only Loop Card:

```text
/lever loop our test suite feels slow. just the card, don't change anything
```

In Codex, select `$lever` and give that same request. Other examples:

```text
/lever arms compare the ideas on the loop card
/lever shepherd keep my stack green till it lands
/lever status
/lever autonomy
```

The router loads the appropriate playbook and dials. Upstream marks its helper
skills `user-invocable: false`; how that appears in a menu depends on the host.
Read-only guidance is usable with the available harness capabilities. Native
Copilot goals, background agents, automations, and entitled model panels need
their real Copilot tools and account access; installing Markdown does not
provide those capabilities in another harness.

For a native Copilot plugin installation on a host with Copilot available,
the pinned checkout can be registered with:

```sh
copilot plugin marketplace add ./vendor/lever
copilot plugin install lever@lever
```

That is an alternative to project-skill discovery for that Copilot context.
Use one registration route to avoid duplicate copies. Copilot is not installed
in this execution environment, so native plugin registration and a Copilot
session were not run here.

## Relationship to the custom workflows

`learn` remains the portable correction evidence ledger. An explicit
`/lever steer` can turn recurring observations into a structural fix, but it
should link the original `learn` evidence instead of inventing user messages or
creating a competing raw-feedback store. `mirror` remains an explicit request
to inspect session history; setup did not harvest it.

An explicitly selected `sdlc` workflow retains BDD/contracts, atomic task graphs,
strict COW requirements, independent evidence review, and stacked squash
delivery. Lever's loop cards, briefs, and shepherding can supply measurements
and operating playbooks within that workload. SkillOpt-Sleep remains the
selected gate for changes to the custom skill instructions.

Automation recipes are installed as files. No automation was created, enabled,
or scheduled, and no issue, PR, label, merge, experiment arm, or transcript
harvest was triggered by setup.

## Checks performed

Tests exercise native and shared-harness installation, relative resources,
repeatability, collisions, dry runs, symlink containment, and preservation of
existing dials and unrelated skills during uninstall. The actual upstream
paired-statistics helper is tested with synthetic local samples: six complete
improving pairs can pass its bar; three stay inconclusive. These fixtures check
the helper, not a measured improvement to this repository.

Help for the statistics, landing-graph, and session-extractor CLIs is checked
without running remote operations or reading private transcripts. Native
Copilot execution, GitHub mutation, and multi-model entitlement remain untested.
