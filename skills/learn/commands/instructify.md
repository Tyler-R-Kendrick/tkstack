---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_instructify
  description: Plan and apply owned, hashed changes to scoped agent instruction files.
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
  - instructify
  defaults:
    argv: []
run:
  skill: skills/instructify
---

# Instructify

Plan and apply owned, hashed changes to scoped agent instruction files.

Routes `instructify [command ...]` and `instructify --help` to the packaged [instructify subskill](../skills/instructify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
