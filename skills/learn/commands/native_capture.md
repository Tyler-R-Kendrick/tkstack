---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_native_capture
  description: Persist actual capture data in the explicitly selected learning store;
    retains native validation.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_capture
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
  - capture
  flags:
    store:
    - --store
    input:
    - --input
  defaults:
    operation: native_capture
    store: null
run:
  artifact: scripts/workflow.lock.json
---

# Native capture

Persist actual capture data in the explicitly selected learning store; retains native validation.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
