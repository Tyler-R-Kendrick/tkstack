---
schema: tkstack.command/v1
tool:
  type: function
  name: instructify_native_apply
  description: Use the existing instruction apply with hashed ownership/stale-plan
    checks.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_apply
      project:
        type: string
        minLength: 1
      plan:
        type: string
        minLength: 1
      dry_run:
        type: boolean
    required:
    - operation
    - project
    - plan
    - dry_run
    additionalProperties: false
cli:
  path:
  - native
  - apply
  flags:
    project:
    - --project
    plan:
    - --plan
    dry_run:
    - --dry-run
  defaults:
    operation: native_apply
    project: .
    dry_run: true
run:
  artifact: scripts/workflow.lock.json
---

# Native apply

Use the existing instruction apply with hashed ownership/stale-plan checks.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
