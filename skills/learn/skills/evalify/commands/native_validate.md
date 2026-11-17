---
schema: tkstack.command/v1
tool:
  type: function
  name: evalify_native_validate
  description: Validate a Promptfoo configuration with a timed receipt.
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
      config:
        type: string
        minLength: 1
      executable:
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
    - config
    - executable
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
    config:
    - --config
    executable:
    - --executable
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

Validate a Promptfoo configuration with a timed receipt.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
