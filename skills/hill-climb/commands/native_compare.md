---
schema: tkstack.command/v1
tool:
  type: function
  name: hill_climb_native_compare
  description: Compare actual retained paired measurements with the existing noise
    and confirmation gate.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_compare
      plan:
        type: string
        minLength: 1
      baseline:
        type: string
        minLength: 1
      candidate:
        type: string
        minLength: 1
      split:
        type: string
        enum:
        - selection
        - confirm
    required:
    - operation
    - plan
    - baseline
    - candidate
    - split
    additionalProperties: false
cli:
  path:
  - native
  - compare
  flags:
    plan:
    - --plan
    baseline:
    - --baseline
    candidate:
    - --candidate
    split:
    - --split
  defaults:
    operation: native_compare
    split: selection
run:
  artifact: scripts/workflow.lock.json
---

# Native compare

Compare actual retained paired measurements with the existing noise and confirmation gate.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
