---
schema: tkstack.command/v1
tool:
  type: function
  name: hookify_native_check
  description: Use the real portable hook check; emitting registration does not establish
    native activation.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_check
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
  - check
  flags:
    rules:
    - --rules
  defaults:
    operation: native_check
run:
  artifact: scripts/workflow.lock.json
---

# Native check

Use the real portable hook check; emitting registration does not establish native activation.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
