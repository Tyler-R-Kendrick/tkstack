---
schema: tkstack.command/v1
tool:
  type: function
  name: codify_native_run
  description: Run the explicitly selected verified artifact through the native Codify
    runtime; preserves its declared code effects and model/profile configuration.
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
      config:
        type:
        - string
        - 'null'
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
    - config
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
    config:
    - --config
    dependencies:
    - --dependencies
    timeout:
    - --timeout
  defaults:
    operation: native_run
    project: .
    config: null
    dependencies: null
    timeout: 30
run:
  artifact: scripts/workflow.lock.json
---

# Native run

Run the explicitly selected verified artifact through the native Codify runtime; preserves its declared code effects and model/profile configuration.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
