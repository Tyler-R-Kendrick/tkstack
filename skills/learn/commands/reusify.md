---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_reusify
  description: Find, assess, and extract reusable code-production assets, including
    init bootstrapping.
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
  - reusify
  defaults:
    argv: []
run:
  skill: skills/reusify
---

# Reusify

Find, assess, and extract reusable code-production assets, including init bootstrapping.

Routes `reusify [command ...]` and `reusify --help` to the packaged [reusify subskill](../skills/reusify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
