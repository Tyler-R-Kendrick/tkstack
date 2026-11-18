---
schema: tkstack.command/v1
tool:
  type: function
  name: codify_native_compile
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
      source:
        type: string
        minLength: 1
      entrypoint:
        type: string
        minLength: 1
      cases:
        type: string
        minLength: 1
      root:
        type:
        - string
        - 'null'
      output:
        type:
        - string
        - 'null'
      include:
        type: array
        items:
          type: string
          minLength: 1
      project:
        type: string
        minLength: 1
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
    required:
    - operation
    - source
    - entrypoint
    - cases
    - root
    - output
    - include
    - project
    - dependencies
    - jobs
    - dry_run
    additionalProperties: false
cli:
  path:
  - native
  - compile
  flags:
    source:
    - --source
    entrypoint:
    - --entrypoint
    cases:
    - --cases
    root:
    - --root
    output:
    - --output
    include:
    - --include
    project:
    - --project
    dependencies:
    - --dependencies
    jobs:
    - --jobs
    dry_run:
    - --dry-run
  defaults:
    operation: native_compile
    root: null
    output: null
    include: []
    project: .
    dependencies: null
    jobs: 4
    dry_run: false
run:
  artifact: scripts/workflow.lock.json
---

# Native compile

Compile supplied code and cases without selecting a separate model or agent harness.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
