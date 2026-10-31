---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_check
  description: Read-only validation using the existing skillify helper.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_check
      target:
        type: string
        minLength: 1
    required:
    - operation
    - target
    additionalProperties: false
cli:
  path:
  - native
  - check
  flags:
    target:
    - --target
  defaults:
    operation: native_check
run:
  artifact: scripts/workflow.lock.json
---

# Native check

Read-only validation using the existing skillify helper.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
