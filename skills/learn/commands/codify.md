---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_codify
  description: Compile a prompt or Markdown procedure into a verified executable lock
    artifact and run it.
  strict: true
  parameters:
    type: object
    properties:
      argv:
        type: array
        items:
          type: string
    required:
    - argv
    additionalProperties: false
cli:
  path:
  - codify
  defaults:
    argv: []
run:
  skill: skills/codify
---

# Codify

Compile a prompt or Markdown procedure into a verified executable lock artifact and run it.

Routes `codify [command ...]` and `codify --help` to the packaged [codify subskill](../skills/codify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
