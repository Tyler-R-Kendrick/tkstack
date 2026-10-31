---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_status
  description: Read the graph, issues, lease owners, expiry, and revision without
    initializing missing state. Tokens are omitted.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - status
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
  - status
  aliases:
  - - status
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
    operation: status
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks status

Read the graph, issues, lease owners, expiry, and revision without initializing missing state. Tokens are omitted.

Invoke `.tkstack/tkstack skills sdlc -- tasks status --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
