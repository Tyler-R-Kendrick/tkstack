---
schema: tkstack.command/v1
tool:
  type: function
  name: evalify_native_run
  description: Score host judgments offline with deterministic Promptfoo assertions.
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
      output:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - cases
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
    cases:
    - --cases
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

Score host judgments offline with deterministic Promptfoo assertions.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
