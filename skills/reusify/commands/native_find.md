---
schema: tkstack.command/v1
tool:
  type: function
  name: reusify_native_find
  description: Find suitable canonical code assets in the existing catalog.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_find
      project:
        type: string
        minLength: 1
      query:
        type: string
        minLength: 1
      limit:
        type: integer
        minimum: 1
        maximum: 100
    required:
    - operation
    - project
    - query
    - limit
    additionalProperties: false
cli:
  path:
  - native
  - find
  flags:
    project:
    - --project
    query:
    - --query
    limit:
    - --limit
  defaults:
    operation: native_find
    project: .
    limit: 10
run:
  artifact: scripts/workflow.lock.json
---

# Native find

Find suitable canonical code assets in the existing catalog.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
