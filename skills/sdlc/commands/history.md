---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_history
  description: Read retained original/revised workloads, ADRs, invalidated results,
    and the ordered event history.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - history
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
  - history
  aliases:
  - - history
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
    operation: history
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks history

Read retained original/revised workloads, ADRs, invalidated results, and the ordered event history.

Invoke `.tkstack/tkstack skills sdlc -- tasks history --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
