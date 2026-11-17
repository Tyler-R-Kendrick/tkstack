---
schema: tkstack.command/v1
tool:
  type: function
  name: constrain_native_audit
  description: Inspect configured constraints in the explicit repository; no writes,
    imports of tests, or inference.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_audit
      repo:
        type: string
        minLength: 1
      category:
        type: string
        enum:
        - source
        - all
        - tests
        - layout
        - artifacts
        - dependencies
        - execution
        - documents
        - boundaries
      staged:
        type: boolean
      strict_dependencies:
        type: boolean
    required:
    - operation
    - repo
    - category
    - staged
    - strict_dependencies
    additionalProperties: false
cli:
  path:
  - native
  - audit
  flags:
    repo:
    - --repo
    category:
    - --category
    staged:
    - --staged
    strict_dependencies:
    - --strict-dependencies
  defaults:
    operation: native_audit
    category: source
    staged: false
    strict_dependencies: false
run:
  artifact: scripts/workflow.lock.json
---

# Native audit

Inspect configured constraints in the explicit repository; no writes, imports of tests, or inference.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
