---
schema: tkstack.command/v1
tool:
  type: function
  name: flowify_native_scaffold
  description: Use the real scaffold for a MAF/Rhai source; native execution remains
    separately observed.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_scaffold
      backend:
        type: string
        enum:
        - maf
        - rhai
      target:
        type: string
        minLength: 1
      name:
        type: string
        minLength: 1
    required:
    - operation
    - backend
    - target
    - name
    additionalProperties: false
cli:
  path:
  - native
  - scaffold
  flags:
    backend:
    - --backend
    target:
    - --target
    name:
    - --name
  defaults:
    operation: native_scaffold
run:
  artifact: scripts/workflow.lock.json
---

# Native scaffold

Use the real scaffold for a MAF/Rhai source; native execution remains separately observed.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
