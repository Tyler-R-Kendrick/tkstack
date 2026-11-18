---
schema: tkstack.command/v1
tool:
  type: function
  name: codify_native_run
  description: Run the verified deterministic artifact without selecting a separate
    model or agent harness.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_run
      artifact:
        type: string
        minLength: 1
      input:
        type: string
        minLength: 1
      project:
        type: string
        minLength: 1
      dependencies:
        type:
        - string
        - 'null'
      timeout:
        type: integer
        minimum: 1
        maximum: 300
    required:
    - operation
    - artifact
    - input
    - project
    - dependencies
    - timeout
    additionalProperties: false
cli:
  path:
  - native
  - run
  flags:
    artifact:
    - --artifact
    input:
    - --input
    project:
    - --project
    dependencies:
    - --dependencies
    timeout:
    - --timeout
  defaults:
    operation: native_run
    project: .
    dependencies: null
    timeout: 30
run:
  artifact: scripts/workflow.lock.json
---

# Native run

Run the verified deterministic artifact without selecting a separate model or agent harness.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
