---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_normalize
  description: Normalize an existing owned skill using the shared explicit contract/profile;
    dry-run stays read-only.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_normalize
      target:
        type: string
        minLength: 1
      profile:
        type: string
        minLength: 1
      dry_run:
        type: boolean
    required:
    - operation
    - target
    - profile
    - dry_run
    additionalProperties: false
cli:
  path:
  - native
  - normalize
  flags:
    target:
    - --target
    profile:
    - --profile
    dry_run:
    - --dry-run
  defaults:
    operation: native_normalize
    dry_run: false
run:
  artifact: scripts/workflow.lock.json
---

# Native normalize

Normalize an existing owned skill using the shared explicit contract/profile; dry-run stays read-only.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
