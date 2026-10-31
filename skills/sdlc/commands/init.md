---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_init
  description: Register a validated graph and retain the immutable initial workload.
    Refuses an existing run ID.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - init
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
      graph:
        type: string
        minLength: 1
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - graph
    additionalProperties: false
cli:
  path:
  - tasks
  - init
  aliases:
  - - init
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
    graph:
    - --graph
  defaults:
    operation: init
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks init

Register a validated graph and retain the immutable initial workload. Refuses an existing run ID.

Invoke `.tkstack/tkstack skills sdlc -- tasks init --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
