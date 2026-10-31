---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_heartbeat
  description: Renew an unexpired lease. A paused task must stop writes and quiesce
    instead.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - heartbeat
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
      ttl:
        type: integer
        minimum: 10
        maximum: 86400
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - task
    - token
    - ttl
    additionalProperties: false
cli:
  path:
  - tasks
  - heartbeat
  aliases:
  - - heartbeat
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
    ttl:
    - --ttl
  defaults:
    operation: heartbeat
    database: null
    repo: null
    scope: workspace
    ttl: 900
run:
  artifact: scripts/workflow.lock.json
---

# Tasks heartbeat

Renew an unexpired lease. A paused task must stop writes and quiesce instead.

Invoke `.tkstack/tkstack skills sdlc -- tasks heartbeat --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
