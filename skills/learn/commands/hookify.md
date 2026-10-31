---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_hookify
  description: Author, replay, and emit mechanically enforceable tool-event policies
    as native hooks.
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
  - hookify
  defaults:
    argv: []
run:
  skill: skills/hookify
---

# Hookify

Author, replay, and emit mechanically enforceable tool-event policies as native hooks.

Routes `hookify [command ...]` and `hookify --help` to the packaged [hookify subskill](../skills/hookify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
