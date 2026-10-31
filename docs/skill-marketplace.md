# Custom skill distribution

All **19 owned packages** live at root `skills/<name>/`. Each contains a matching
`SKILL.md`, license, conditional Markdown references, and its required local
resources. The root `.claude-plugin/marketplace.json` has one entry per package.

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

For a skills CLI installation from a checkout:

```sh
npx skills add . --skill investigate --skill write --skill document
```

For a published checkout, substitute `Tyler-R-Kendrick/tkstack` for `.`. Add any
other package names explicitly. These commands are distribution instructions;
they do not claim a remote revision contains the local uncommitted changes.

For Claude's marketplace interface:

```text
/plugin marketplace add /absolute/path/to/tkstack
/plugin install investigate@tkstack
/plugin install write@tkstack
/plugin install document@tkstack
```

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
