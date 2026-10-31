---
schema: tkstack.command/v1
tool:
  type: function
  name: normalize_labels
  description: Trim, deduplicate, and sort labels.
  strict: true
  parameters:
    type: object
    properties:
      labels:
        type: array
        items:
          type: string
    required:
    - labels
    additionalProperties: false
cli:
  path:
  - labels
  - normalize
  aliases:
  - - normalize
  - - labels
    - norm
  flags:
    labels:
    - --labels
    - -l
run:
  artifact: scripts/workflow.lock.json
---

# Normalize labels

Invoke `labels normalize --labels '[" b ", "a", "a"]'` or `normalize -l '["b", "a"]'`.
The JSON tool call takes `labels` with the same array-of-strings contract.
Returns sorted unique trimmed labels; rejects other input before execution.
