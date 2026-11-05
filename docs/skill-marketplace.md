# Custom skill distribution

All **19 packages** ship in **12 plugins**: 8 skills under development live at
root `skills/<name>/`, the four third-party-derived packages (`fal-ai`,
`headroom`, `open-design`, `rtk`) live at `.agents/skills/<name>/`, and Learn
carries 7 subskills (`codify`, `flowify`, `hookify`, `instructify`, `lintify`,
`reusify`, `skillify`) at `skills/learn/skills/<name>/`. Each contains a matching
`SKILL.md`, license, conditional Markdown references, and its required local
resources. The root `.claude-plugin/marketplace.json` has one entry per root
package; installing `learn@tkstack` installs its subskills as `/learn <name>`.

| Area | Packages |
| --- | --- |
| Engineering | `tkstack-principles`, `investigate`, `sdlc` |
| Learning and authoring | `learn`, `skillify`, `codify`, `reusify`, `lintify`, `hookify`, `instructify`, `flowify` |
| Quality and optimization | `unslop`, `hill-climb` |
| Knowledge and writing | `document`, `write` |
| Design, media, context | `open-design`, `fal-ai`, `headroom`, `rtk` |

Packages follow the [Agent Skills specification](https://agentskills.io/specification)
and root [skills discovery](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md).
The entrypoint carries purpose, triggers, the execution spine, boundaries, and
condition-to-reference pointers. Detailed procedures and provenance live under
`references/`; templates and scripts stay local to the selected package.

Install one published package with the skills CLI. `skills` 1.7.6 `--help`
shows `add <package>` as `owner/repo` (for example `vercel-labs/agent-skills`)
and `--skill` as the SKILL.md name:

```sh
npx skills add Tyler-R-Kendrick/tkstack --skill investigate
```

The `investigate` package's tree path is `skills/investigate`. This command
names that manifest package and path. `--list` on skills 1.7.6 resolves the
source to `https://github.com/Tyler-R-Kendrick/tkstack.git`
(`skills/investigate`) and finds one skill named `investigate`:

```sh
npx skills add Tyler-R-Kendrick/tkstack/skills/investigate
```

Other real packages are `document`
(`skills/document`), `write` (`skills/write`), `fal-ai`
(`.agents/skills/fal-ai`), `headroom` (`.agents/skills/headroom`),
`hill-climb` (`skills/hill-climb`), `learn` (`skills/learn`), `open-design`
(`.agents/skills/open-design`), `rtk` (`.agents/skills/rtk`), `sdlc`
(`skills/sdlc`), `tkstack-principles` (`skills/tkstack-principles`), and
`unslop` (`skills/unslop`). From a local checkout, replace the GitHub source
with the same relative path, for example `./skills/investigate`.

Add the marketplace, then install one plugin. These are Claude Code slash
commands. The `investigate` plugin source in `.claude-plugin/marketplace.json`
is `./skills/investigate`:

```text
/plugin marketplace add Tyler-R-Kendrick/tkstack
/plugin install investigate@tkstack
```

The same form works for `write@tkstack` (`./skills/write`) and
`document@tkstack` (`./skills/document`). These commands are distribution
instructions; they do not claim a remote revision contains local uncommitted
changes.

Use a single installation route for a package to avoid duplicate names.
The dotfiles route installs all pinned and owned skills into selected harnesses:

```sh
python3 scripts/install.py --target /path/to/project
python3 scripts/doctor.py --target /path/to/project
```

Standalone packages cannot assume sibling skills, vendor trees, or the dotfiles
launchers exist. Guidance is portable; actual helpers, models, native adapters,
provider services, COW volumes, and credentials must be available for their
respective execution paths. A copied skill does not activate those capabilities.
Keep absent evidence and runtime requirements explicit.

See [source selection and validation limits](skill-distillation.md),
[authoring](authoring.md), and [evolution](skill-evolution.md). Explicit authoring
uses meaningful engineering validation; automatic revision search preserves the
configured SkillOpt acceptance gate. Packaging checks are not performance claims.
