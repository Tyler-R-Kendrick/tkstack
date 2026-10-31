---
schema: tkstack.command/v1
tool:
  type: function
  name: unslop_native_check
  description: Use the actual scoped anti-slop check; recorded observations do not
    replace artifact inspection.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_check
      store:
        type:
        - string
        - 'null'
    required:
    - operation
    - store
    additionalProperties: false
cli:
  path:
  - native
  - check
  flags:
    store:
    - --store
  defaults:
    operation: native_check
    store: null
run:
  artifact: scripts/workflow.lock.json
---

# Native check

Use the actual scoped anti-slop check; recorded observations do not replace artifact inspection.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
