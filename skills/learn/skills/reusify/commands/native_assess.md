---
schema: tkstack.command/v1
tool:
  type: function
  name: reusify_native_assess
  description: Read actual source observations and assess reuse evidence without generating
    or changing code.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_assess
      project:
        type: string
        minLength: 1
      input:
        type: string
        minLength: 1
      jobs:
        type: integer
        minimum: 1
        maximum: 16
    required:
    - operation
    - project
    - input
    - jobs
    additionalProperties: false
cli:
  path:
  - native
  - assess
  flags:
    project:
    - --project
    input:
    - --input
    jobs:
    - --jobs
  defaults:
    operation: native_assess
    project: .
    jobs: 4
run:
  artifact: scripts/workflow.lock.json
---

# Native assess

Read actual source observations and assess reuse evidence without generating or changing code.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
