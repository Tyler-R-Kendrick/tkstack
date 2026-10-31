---
schema: tkstack.command/v1
tool:
  type: function
  name: flowify_model
  description: Read the skill contract model, required evidence and explicit semantic/native
    boundaries without executing the procedure.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - model
    required:
    - operation
    additionalProperties: false
cli:
  path:
  - model
  flags: {}
  defaults:
    operation: model
run:
  artifact: scripts/workflow.lock.json
---

# Model

Read the skill contract model, required evidence and explicit semantic/native boundaries without executing the procedure.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
