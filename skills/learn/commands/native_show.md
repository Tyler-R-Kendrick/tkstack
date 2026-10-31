---
schema: tkstack.command/v1
tool:
  type: function
  name: learn_native_show
  description: Read the learning ledger as JSON without initializing a missing store.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_show
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
  - show
  flags:
    store:
    - --store
  defaults:
    operation: native_show
    store: null
run:
  artifact: scripts/workflow.lock.json
---

# Native show

Read the learning ledger as JSON without initializing a missing store.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
