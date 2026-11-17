---
schema: tkstack.command/v1
tool:
  type: function
  name: testify_native_create
  description: Create an absent Python CLI contract test from an explicit reviewed
    case specification.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_create
      project:
        type: string
        minLength: 1
      target:
        type: string
        minLength: 1
      spec:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - target
    - spec
    additionalProperties: false
cli:
  path:
  - native
  - create
  flags:
    project:
    - --project
    target:
    - --target
    spec:
    - --spec
  defaults:
    operation: native_create
run:
  artifact: scripts/workflow.lock.json
---

# Native create

Create an absent Python CLI contract test from an explicit reviewed case specification.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
