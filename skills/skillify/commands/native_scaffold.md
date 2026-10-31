---
schema: tkstack.command/v1
tool:
  type: function
  name: skillify_native_scaffold
  description: Create a draft with the actual skillify generator; refuses an existing
    target.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_scaffold
      name:
        type: string
        minLength: 1
      description:
        type: string
        minLength: 1
      target:
        type: string
        minLength: 1
      backend:
        type: string
        enum:
        - python
        - ai-sdk
    required:
    - operation
    - name
    - description
    - target
    - backend
    additionalProperties: false
cli:
  path:
  - native
  - scaffold
  flags:
    name:
    - --name
    description:
    - --description
    target:
    - --target
    backend:
    - --backend
  defaults:
    operation: native_scaffold
    backend: python
run:
  artifact: scripts/workflow.lock.json
---

# Native scaffold

Create a draft with the actual skillify generator; refuses an existing target.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
