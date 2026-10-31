---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_lintify
  description: Create or configure a native CLI lint rule and validate it against
    real fixtures.
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
  - lintify
  defaults:
    argv: []
run:
  skill: skills/lintify
---

# Lintify

Create or configure a native CLI lint rule and validate it against real fixtures.

Routes `lintify [command ...]` and `lintify --help` to the packaged [lintify subskill](../skills/lintify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
