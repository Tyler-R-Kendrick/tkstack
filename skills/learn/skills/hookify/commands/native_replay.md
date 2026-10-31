---
schema: tkstack.command/v1
tool:
  type: function
  name: hookify_native_replay
  description: Use the real portable hook replay; emitting registration does not establish
    native activation.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_replay
      rules:
        type: string
        minLength: 1
      cases:
        type: string
        minLength: 1
      jobs:
        type: integer
        minimum: 1
        maximum: 16
    required:
    - operation
    - rules
    - cases
    - jobs
    additionalProperties: false
cli:
  path:
  - native
  - replay
  flags:
    rules:
    - --rules
    cases:
    - --cases
    jobs:
    - --jobs
  defaults:
    operation: native_replay
    jobs: 4
run:
  artifact: scripts/workflow.lock.json
---

# Native replay

Use the real portable hook replay; emitting registration does not establish native activation.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
