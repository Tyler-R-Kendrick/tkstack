# Source analogues and adaptations

Reviewed 2026-10-30. This owned package uses ideas from these primary sources;
it does not install or modify the source packages.

- Pstack's [authoring-a-skill playbook](https://github.com/poteto/plugins/blob/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md):
  clear agent-facing instructions, metadata/reference checks, and meaningful
  structural tests. Its dependency on Cursor's built-in `create-skill` becomes
  a portable owned procedure and an optional offline helper here.
- Pstack's [automate-me at 4dd1d05](https://github.com/cursor/plugins/blob/4dd1d05818d19792e7cd6e818f1667f95f7e1dbe/pstack/skills/automate-me/SKILL.md):
  inspect the existing skill, use actual scoped evidence, update rather than
  duplicate, preserve the user's conventions, reference rather than restate,
  and avoid overfitting to inferred preferences.
- Pstack's [reflect at the pinned revision](https://github.com/poteto/plugins/blob/74dd2291e8e37b12fd6dc49b2acbd655c6bdaf12/pstack/skills/reflect/SKILL.md):
  distinguish useful procedural changes from rules better implemented in code,
  and route a finding to the appropriate durable layer. We do not import its
  mandatory agent fan-out, tracker writes, or extra approval ceremony.
- Anthropic's [skill-creator](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/skill-creator/skills/skill-creator/SKILL.md)
  and [skill-development](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/plugin-dev/skills/skill-development/SKILL.md):
  capture task intent, make triggers specific, use progressive disclosure,
  extract deterministic scripts, test against meaningful cases, distinguish
  structural validation from performance, and iterate from actual feedback.

The checked Pstack trees have authoring workflows, not an exact `skillify`
skill. Anthropic's older `anthropics/claude-code/plugins/` links returned 404;
the source is now available in `anthropics/claude-plugins-official` at the pinned
revision above. We do not claim a nonexistent exact-name upstream skill.

Tkstack adaptations follow the user's stronger deterministic-first and bounded
concurrency preferences. No private transcript mining, automatic model trials,
forced provider/model selection, unrequested publication, or redundant approval
is copied from an analogue. The existing `learn` evidence model and SkillOpt
revision gate remain authoritative where their scope applies. A checked package
is not proof that its model-trigger behavior or creative quality improved.
