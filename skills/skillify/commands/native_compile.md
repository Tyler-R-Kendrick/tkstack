---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_compile
  description: Compile supplied native code and actual contract cases with the existing
    skillify compiler. Cases can execute their declared effects/inference; retain
    actual authorization and explicit profiles.
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
      config:
        type:
        - string
        - 'null'
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
    - profile
    - dependencies
    - jobs
    - dry_run
    - config
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
    profile:
    - --profile
    dependencies:
    - --dependencies
    jobs:
    - --jobs
    dry_run:
    - --dry-run
    config:
    - --config
    project:
    - --project
    timeout:
    - --timeout
    include:
    - --include
  defaults:
    operation: native_compile
    entrypoint: null
    profile: []
    dependencies: null
    jobs: 4
    dry_run: false
    config: null
    project: .
    timeout: 30
    include: []
run:
  artifact: scripts/workflow.lock.json
---

# Native compile

Compile supplied native code and actual contract cases with the existing skillify compiler. Cases can execute their declared effects/inference; retain actual authorization and explicit profiles.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
