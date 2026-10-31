---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_native_experience
  description: Persist actual experience data in the explicitly selected learning
    store; retains native validation.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_experience
      store:
        type:
        - string
        - 'null'
      input:
        type: string
        minLength: 1
    required:
    - operation
    - store
    - input
    additionalProperties: false
cli:
  path:
  - native
  - experience
  flags:
    store:
    - --store
    input:
    - --input
  defaults:
    operation: native_experience
    store: null
run:
  artifact: scripts/workflow.lock.json
---

# Native experience

Persist actual experience data in the explicitly selected learning store; retains native validation.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
