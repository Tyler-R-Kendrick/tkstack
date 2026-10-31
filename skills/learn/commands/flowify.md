---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_flowify
  description: Create and validate a reusable executable workflow in an existing DSL
    such as MAF YAML or Rhai.
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
  - flowify
  defaults:
    argv: []
run:
  skill: skills/flowify
---

# Flowify

Create and validate a reusable executable workflow in an existing DSL such as MAF YAML or Rhai.

Routes `flowify [command ...]` and `flowify --help` to the packaged [flowify subskill](../skills/flowify/SKILL.md). Its own command files define the typed signatures, and its own lock binds execution.
