---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_compile
  description: Compile supplied code and cases without selecting a separate model
    or agent harness.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_compile
      target:
        type: string
        minLength: 1
      cases:
        type: string
        minLength: 1
      entrypoint:
        type:
        - string
        - 'null'
      dependencies:
        type:
        - string
        - 'null'
      jobs:
        type: integer
        minimum: 1
        maximum: 16
      dry_run:
        type: boolean
      project:
        type: string
        minLength: 1
      timeout:
        type: integer
        minimum: 1
        maximum: 300
      include:
        type: array
        items:
          type: string
          minLength: 1
    required:
    - operation
    - target
    - cases
    - entrypoint
    - dependencies
    - jobs
    - dry_run
    - project
    - timeout
    - include
    additionalProperties: false
cli:
  path:
  - native
  - compile
  flags:
    target:
    - --target
    cases:
    - --cases
    entrypoint:
    - --entrypoint
    dependencies:
    - --dependencies
    jobs:
    - --jobs
    dry_run:
    - --dry-run
    project:
    - --project
    timeout:
    - --timeout
    include:
    - --include
  defaults:
    operation: native_compile
    entrypoint: null
    dependencies: null
    jobs: 4
    dry_run: false
    project: .
    timeout: 30
    include: []
run:
  artifact: scripts/workflow.lock.json
---

# Native compile

Compile supplied code and cases without selecting a separate model or agent harness.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
