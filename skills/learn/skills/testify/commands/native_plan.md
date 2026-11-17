---
schema: tkstack.command/v1
tool:
  type: function
  name: testify_native_plan
  description: Preview the generated Python CLI contract test without writes.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_plan
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
  - plan
  flags:
    project:
    - --project
    target:
    - --target
    spec:
    - --spec
  defaults:
    operation: native_plan
run:
  artifact: scripts/workflow.lock.json
---

# Native plan

Preview the generated Python CLI contract test without writes.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
