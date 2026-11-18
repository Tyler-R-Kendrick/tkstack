---
schema: tkstack.command/v1
tool:
  type: function
  name: evalify_native_validate
  description: Validate host-judged cases and retain a timed receipt.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_validate
      project:
        type: string
        minLength: 1
      cases:
        type: string
        minLength: 1
      receipt:
        type: string
        minLength: 1
      timeout:
        type: integer
        minimum: 1
        maximum: 25
    required:
    - operation
    - project
    - cases
    - receipt
    - timeout
    additionalProperties: false
cli:
  path:
  - native
  - validate
  flags:
    project:
    - --project
    cases:
    - --cases
    receipt:
    - --receipt
    timeout:
    - --timeout
  defaults:
    operation: native_validate
    timeout: 20
run:
  artifact: scripts/workflow.lock.json
---

# Native validate

Validate host-judged cases and retain a timed receipt.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
