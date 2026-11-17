---
schema: tkstack.command/v1
tool:
  type: function
  name: evalify_native_run
  description: Run Promptfoo with a bounded timeout and timed receipt.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_run
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
      output:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - config
    - executable
    - receipt
    - timeout
    - output
    additionalProperties: false
cli:
  path:
  - native
  - run
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
    output:
    - --output
  defaults:
    operation: native_run
    timeout: 20
run:
  artifact: scripts/workflow.lock.json
---

# Native run

Run Promptfoo with a bounded timeout and timed receipt.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
