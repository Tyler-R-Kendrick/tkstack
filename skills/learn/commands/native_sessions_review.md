---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_native_sessions_review
  description: Read and consolidate only selected session IDs; save is an explicit
    write.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_sessions_review
      session:
        type: array
        items:
          type: string
          minLength: 1
      save:
        type: boolean
      jobs:
        type: integer
        minimum: 1
        maximum: 16
    required:
    - operation
    - session
    - save
    - jobs
    additionalProperties: false
cli:
  path:
  - native
  - sessions
  - review
  flags:
    session:
    - --session
    save:
    - --save
    jobs:
    - --jobs
  defaults:
    operation: native_sessions_review
    session: []
    save: false
    jobs: 4
run:
  artifact: scripts/workflow.lock.json
---

# Native sessions review

Read and consolidate only selected session IDs; save is an explicit write.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
