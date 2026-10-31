---
schema: tkstack.command/v1
tool:
  type: function
  name: hookify_native_emit
  description: Use the real portable hook emit; emitting registration does not establish
    native activation.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_emit
      rules:
        type: string
        minLength: 1
    required:
    - operation
    - rules
    additionalProperties: false
cli:
  path:
  - native
  - emit
  flags:
    rules:
    - --rules
  defaults:
    operation: native_emit
run:
  artifact: scripts/workflow.lock.json
---

# Native emit

Use the real portable hook emit; emitting registration does not establish native activation.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
