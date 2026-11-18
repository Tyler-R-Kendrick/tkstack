---
schema: tkstack.command/v1
tool:
  type: function
  name: lintify_native_scaffold
  description: Create the existing deterministic ESLint or Lintbook example package.
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
        - eslint
        - lintbook
      target:
        type: string
        minLength: 1
    required:
    - operation
    - backend
    - target
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
  defaults:
    operation: native_scaffold
run:
  artifact: scripts/workflow.lock.json
---

# Native scaffold

Create the existing deterministic ESLint or Lintbook example package.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
