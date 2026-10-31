---
schema: tkstack.command/v1
tool:
  type: function
  name: reusify_native_check
  description: Check the real reuse catalog without executing any asset.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_check
      project:
        type: string
        minLength: 1
      catalog:
        type: string
        minLength: 1
    required:
    - operation
    - project
    - catalog
    additionalProperties: false
cli:
  path:
  - native
  - check
  flags:
    project:
    - --project
    catalog:
    - --catalog
  defaults:
    operation: native_check
    project: .
    catalog: .tkstack/reuse/catalog.json
run:
  artifact: scripts/workflow.lock.json
---

# Native check

Check the real reuse catalog without executing any asset.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
