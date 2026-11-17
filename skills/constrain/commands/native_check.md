---
schema: tkstack.command/v1
tool:
  type: function
  name: constrain_native_check
  description: Enforce configured constraints in the explicit repository; no writes,
    imports of tests, or inference.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_check
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
  - check
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
    operation: native_check
    category: source
    staged: false
    strict_dependencies: false
run:
  artifact: scripts/workflow.lock.json
---

# Native check

Enforce configured constraints in the explicit repository; no writes, imports of tests, or inference.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
