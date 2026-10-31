# Glossary

| Term | Meaning |
| --- | --- |
| Source | An upstream repository or package pinned in `sources.lock.json` |
| Snapshot | The exact upstream files retained under `vendor/<source>/` |
| Skill | A directory containing `SKILL.md` and its supporting files |
| Subskill | A complete skill package nested at `<parent>/skills/<name>/` that ships inside its parent, installs only through it, and is exposed as the parent's `<name>` subcommand by a mount command (`run: {skill: skills/<name>}`) |
| Code-mode prompt | A skill's thin discovery/invocation context that directs the agent to call an executable tool rather than reconstruct its procedure |
| Executable skill workflow | The canonical workflow definition and bindings in a skill's `scripts/`, with validated inputs/outputs, gates, effects, and failure behavior |
| Inference profile | Explicit provider/model/API or harness configuration for residual inference; separate from deterministic workflow control flow |
| Alias | An installed skill name used to resolve an upstream name collision |
| View | A generated copy of a source's skill tree with aliases and calls rewritten |
| Harness | An agent host such as Codex, Claude Code, or Cursor |
| Target | A home or project directory receiving the installation links |
| Pstack baseline | The preferred engineering entry point, `poteto-mode` and its principles |
| Tkstack principles | Personal deterministic-first and concurrency-by-design standards in `skills/tkstack-principles` |
| Decision tier | Deterministic code/rules, then constrained decision models/APIs, then residual LLM/agent judgment |
| Reuse asset | A canonical template, snippet, generator, module, library, or component with a discoverable interface and invocation |
| Reuse occurrence | A distinct meaningful implementation or separately identified requested use; aliases and generated copies are not independent implementation evidence |
| Local skill state | Session/repository/workspace bookkeeping under `.tkstack/`, protected by its local ignore policy; separate from authored deliverables |
| Codified lock | A verified code-bearing workflow artifact produced from a prompt/Markdown-derived implementation; subsequent runs execute frozen native code and reject source drift. |
| Tkstack storage scope | Workspace, user, or global `.tkstack` root; read nearest first and write only to the explicit selected root. |
| Temporary session | Ignored `sessions/<session>/` evidence/scratch directory; consolidate useful findings before discarding it. |
| Session consolidation | Review actual session evidence, abstract transferable principles, choose the smallest durable mechanisms, and verify resulting reusable artifacts. |
