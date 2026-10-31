---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_skillify
  description: Create, convert, normalize, check, and compile owned portable skills.
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
  - skillify
  defaults:
    argv: []
run:
  skill: skills/skillify
---

# Skillify

Create, convert, normalize, check, and compile owned portable skills.

Routes `skillify [command ...]` and `skillify --help` to the packaged [skillify subskill](../skills/skillify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
