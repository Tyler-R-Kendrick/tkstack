# Skills under development

This directory is reserved for skills under active development. Skills installed
from or wrapping an outside source do not belong here: harness-independent ones
are committed in `.agents/skills/` (or pinned under `vendor/`), and Cursor-only
packages such as Pstack install into `.cursor/skills/`.

Add each skill as `<name>/SKILL.md`, keeping references, templates, and scripts in
the same directory. The installer links each complete root package. Names must
be unique after source-specific aliasing.

A package can ship complete subskills at `<name>/skills/<subskill>/`, each with
its own `SKILL.md`, `commands/`, `scripts/`, `references/`, license, and lock.
Subskills install and publish only inside their parent, which mounts each one as
a subcommand: list them in the parent contract's `subskills` map and run
Skillify normalize to generate `commands/<subskill>.md`. Learn packages the seven
___ify skills this way (`/learn skillify ...`, or
`.tkstack/tkstack skills learn -- skillify ...`).

Keep upstream edits out of this directory and out of `vendor/`. Configure a
name collision in `harnesses/skills.json`; the installer generates the adapted
view under `.tkstack/`. Personal skills join all selected harnesses on install.

These 8 root packages and Learn's 7 subskills, plus the four
third-party-derived packages in `.agents/skills/`, are compatible with the
[Agent Skills format](https://agentskills.io/specification) and
[skills.sh discovery](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md).
Keep their relative resources and licenses self-contained: marketplace clients
may copy only the selected skill directory. The root
`.claude-plugin/marketplace.json` catalogs each root package separately; Learn's
entry carries its subskills.
See [distribution](../docs/skill-marketplace.md) and
[skill evolution](../docs/skill-evolution.md).

Keep entrypoints concise with explicit condition-to-reference pointers. Put
detailed procedures, variants, and provenance in each package's `references/`
folder. Avoid required sibling/vendor imports so each copied package works on
its own. See [the full catalog distillation](../docs/skill-distillation.md).

See `docs/standards.md` for the combined setup's routing defaults and
`docs/skills.md` for the current inventory.

Use [Codify](learn/skills/codify/SKILL.md) for reusable prompt/Markdown compilation and
verified executable lock artifacts; Skillify consumes its shared engine.
