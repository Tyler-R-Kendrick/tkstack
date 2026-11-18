---
schema: tkstack.command/v1
tool:
  type: function
  name: hill_climb_native_experiment
  description: Run a scoped Git experiment action from an explicit JSON request.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_experiment
      request:
        type: string
        minLength: 1
    required:
    - operation
    - request
    additionalProperties: false
cli:
  path:
  - native
  - experiment
  flags:
    request:
    - --request
  defaults:
    operation: native_experiment
run:
  artifact: scripts/workflow.lock.json
  timeout_seconds: 86400
---

# Native experiment

Run a scoped Git experiment action from an explicit JSON request.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
