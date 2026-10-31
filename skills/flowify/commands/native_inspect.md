---
schema: tkstack.command/v1
tool:
  type: function
  name: flowify_native_inspect
  description: Use the real inspect for a MAF/Rhai source; native execution remains
    separately observed.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_inspect
      backend:
        type: string
        enum:
        - maf
        - rhai
      file:
        type: string
        minLength: 1
    required:
    - operation
    - backend
    - file
    additionalProperties: false
cli:
  path:
  - native
  - inspect
  flags:
    backend:
    - --backend
    file:
    - --file
  defaults:
    operation: native_inspect
run:
  artifact: scripts/workflow.lock.json
---

# Native inspect

Use the real inspect for a MAF/Rhai source; native execution remains separately observed.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
