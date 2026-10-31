---
schema: tkstack.command/v1
tool:
  type: function
  name: headroom_verify
  description: Validate a retained workload report against the skill contract, criterion
    coverage and actual evidence hashes. Semantic review is recorded, not authenticated.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - verify
      report:
        type: string
        minLength: 1
    required:
    - operation
    - report
    additionalProperties: false
cli:
  path:
  - verify
  flags:
    report:
    - --report
  defaults:
    operation: verify
run:
  artifact: scripts/workflow.lock.json
---

# Verify

Validate a retained workload report against the skill contract, criterion coverage and actual evidence hashes. Semantic review is recorded, not authenticated.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
