---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_gate
  description: Check that all current tasks have fresh accepted proof and no open
    issues. Also run the existing independent original-workload evidence and live
    PR gates.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - gate
      run:
        type: string
        minLength: 1
      actor:
        type: string
        minLength: 1
      database:
        type:
        - string
        - 'null'
      repo:
        type:
        - string
        - 'null'
      scope:
        type: string
        enum:
        - workspace
        - user
        - global
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    additionalProperties: false
cli:
  path:
  - tasks
  - gate
  aliases:
  - - gate
  flags:
    run:
    - --run
    actor:
    - --actor
    database:
    - --database
    repo:
    - --repo
    scope:
    - --scope
  defaults:
    operation: gate
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks gate

Check that all current tasks have fresh accepted proof and no open issues. Also run the existing independent original-workload evidence and live PR gates.

Invoke `.tkstack/tkstack skills sdlc -- tasks gate --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
