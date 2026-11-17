---
schema: tkstack.command/v1
tool:
  type: function
  name: testify_native_run
  description: Execute one selected Python test with caller authority and report the
    real exit.
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
      target:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - target
    additionalProperties: false
cli:
  path:
  - native
  - run
  flags:
    project:
    - --project
    target:
    - --target
  defaults:
    operation: native_run
run:
  artifact: scripts/workflow.lock.json
---

# Native run

Execute one selected Python test with caller authority and report the real exit.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
