---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_testify
  description: Design, create, run and fault-check a distinct behavioral test with
    an independent oracle.
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
  - testify
  defaults:
    argv: []
run:
  skill: skills/testify
---

# Testify

Design, create, run and fault-check a distinct behavioral test with an independent oracle.

Routes `testify [command ...]` and `testify --help` to the packaged [testify subskill](../skills/testify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
