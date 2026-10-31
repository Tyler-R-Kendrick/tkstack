---
schema: tkstack.command/v1
tool:
  type: function
  name: unslop_native_grade
  description: Use the actual scoped anti-slop grade; recorded observations do not
    replace artifact inspection.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_grade
      store:
        type:
        - string
        - 'null'
      input:
        type: string
        minLength: 1
    required:
    - operation
    - store
    - input
    additionalProperties: false
cli:
  path:
  - native
  - grade
  flags:
    store:
    - --store
    input:
    - --input
  defaults:
    operation: native_grade
    store: null
run:
  artifact: scripts/workflow.lock.json
---

# Native grade

Use the actual scoped anti-slop grade; recorded observations do not replace artifact inspection.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
