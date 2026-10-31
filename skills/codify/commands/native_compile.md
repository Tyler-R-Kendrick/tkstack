---
schema: tkstack.command/v1
tool:
  type: function
  name: codify_native_compile
  description: Compile supplied native code and actual contract cases with the existing
    codify compiler. Cases can execute their declared effects/inference; retain actual
    authorization and explicit profiles.
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
      config:
        type:
        - string
        - 'null'
      project:
        type: string
        minLength: 1
      profile:
        type: array
        items:
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
    - config
    - project
    - profile
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
    config:
    - --config
    project:
    - --project
    profile:
    - --profile
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
    config: null
    project: .
    profile: []
    dependencies: null
    jobs: 4
    dry_run: false
run:
  artifact: scripts/workflow.lock.json
---

# Native compile

Compile supplied native code and actual contract cases with the existing codify compiler. Cases can execute their declared effects/inference; retain actual authorization and explicit profiles.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
