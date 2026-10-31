---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_finish
  description: Release your current lease. Done requires current task/head/workload/input-bound
    proof; blocked and retry acknowledge that writes have stopped.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - finish
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
      task:
        type: string
        minLength: 1
      token:
        type: string
        minLength: 1
      outcome:
        type: string
        enum:
        - done
        - blocked
        - retry
      head:
        type:
        - string
        - 'null'
      proof:
        type:
        - string
        - 'null'
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - task
    - token
    - outcome
    - head
    - proof
    additionalProperties: false
cli:
  path:
  - tasks
  - finish
  aliases:
  - - finish
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
    task:
    - --task
    token:
    - --token
    outcome:
    - --outcome
    head:
    - --head
    proof:
    - --proof
  defaults:
    operation: finish
    database: null
    repo: null
    scope: workspace
    head: null
    proof: null
run:
  artifact: scripts/workflow.lock.json
---

# Tasks finish

Release your current lease. Done requires current task/head/workload/input-bound proof; blocked and retry acknowledge that writes have stopped.

Invoke `.tkstack/tkstack skills sdlc -- tasks finish --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
