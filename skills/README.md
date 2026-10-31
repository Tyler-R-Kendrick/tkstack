# Personal skills

Add each skill as `<name>/SKILL.md`, keeping references, templates, and scripts in
the same directory. The installer finds skill directories recursively and links
the complete directory. Names must be unique after source-specific aliasing.

Keep upstream edits out of this directory and out of `vendor/`. Configure a
name collision in `harnesses/skills.json`; the installer generates the adapted
view under `.tkstack/`. Personal skills join all selected harnesses on install.

All 19 owned packages are canonical root skills compatible with the
[Agent Skills format](https://agentskills.io/specification) and
[skills.sh discovery](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md).
Keep their relative resources and licenses self-contained: marketplace clients
may copy only the selected skill directory. The root
`.claude-plugin/marketplace.json` catalogs each package separately.
See [distribution](../docs/skill-marketplace.md) and
[skill evolution](../docs/skill-evolution.md).

Keep entrypoints concise with explicit condition-to-reference pointers. Put
detailed procedures, variants, and provenance in each package's `references/`
folder. Avoid required sibling/vendor imports so each copied package works on
its own. See [the full catalog distillation](../docs/skill-distillation.md).

See `docs/standards.md` for the combined setup's routing defaults and
`docs/skills.md` for the current inventory.

Use [Codify](codify/SKILL.md) for reusable prompt/Markdown compilation and
verified executable lock artifacts; Skillify consumes its shared engine.
