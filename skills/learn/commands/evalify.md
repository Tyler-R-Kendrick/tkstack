---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_evalify
  description: Design and run calibrated evaluations for nondeterministic outputs
    with an established framework.
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
  - evalify
  defaults:
    argv: []
run:
  skill: skills/evalify
---

# Evalify

Design and run calibrated evaluations for nondeterministic outputs with an established framework.

Routes `evalify [command ...]` and `evalify --help` to the packaged [evalify subskill](../skills/evalify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
