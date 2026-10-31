---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_convert
  description: Plan or apply the existing owned-skill conversion without overwriting
    native helpers.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_convert
      target:
        type: string
        minLength: 1
      dry_run:
        type: boolean
    required:
    - operation
    - target
    - dry_run
    additionalProperties: false
cli:
  path:
  - native
  - convert
  flags:
    target:
    - --target
    dry_run:
    - --dry-run
  defaults:
    operation: native_convert
    dry_run: false
run:
  artifact: scripts/workflow.lock.json
---

# Native convert

Plan or apply the existing owned-skill conversion without overwriting native helpers.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
