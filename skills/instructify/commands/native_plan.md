---
schema: tkstack.command/v1
tool:
  type: function
  name: instructify_native_plan
  description: Use the existing instruction plan with hashed ownership/stale-plan
    checks.
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
      input:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - input
    additionalProperties: false
cli:
  path:
  - native
  - plan
  flags:
    project:
    - --project
    input:
    - --input
  defaults:
    operation: native_plan
    project: .
run:
  artifact: scripts/workflow.lock.json
---

# Native plan

Use the existing instruction plan with hashed ownership/stale-plan checks.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
