---
schema: tkstack.command/v1
tool:
  type: function
  name: constrain_native_mutate
  description: Execute selected Cosmic Ray mutations in isolated Git snapshots, with
    bounded unittest cases and a new evidence receipt.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - native_mutate
      repo:
        type: string
        minLength: 1
      plan:
        type: string
        minLength: 1
      engine:
        type: string
        minLength: 1
      output:
        type: string
        minLength: 1
      test_timeout:
        type: integer
        minimum: 1
        maximum: 120
      total_timeout:
        type: integer
        minimum: 1
        maximum: 540
      baseline_repetitions:
        type: integer
        minimum: 1
        maximum: 5
    required:
    - operation
    - repo
    - plan
    - engine
    - output
    - test_timeout
    - total_timeout
    - baseline_repetitions
    additionalProperties: false
cli:
  path:
  - native
  - mutate
  flags:
    repo:
    - --repo
    plan:
    - --plan
    engine:
    - --engine
    output:
    - --output
    test_timeout:
    - --test-timeout
    total_timeout:
    - --total-timeout
    baseline_repetitions:
    - --baseline-repetitions
  defaults:
    operation: native_mutate
    test_timeout: 15
    total_timeout: 300
    baseline_repetitions: 2
run:
  artifact: scripts/workflow.lock.json
  timeout_seconds: 900
---

# Native mutate

Execute selected Cosmic Ray mutations in isolated Git snapshots, with bounded unittest cases and a new evidence receipt.

[Execution contract](../references/execution.md) describes effects, paths, evidence, and limitations. Frontmatter defines the exact typed signature.
