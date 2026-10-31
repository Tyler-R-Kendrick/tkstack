---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_claim
  description: Atomically lease ready work within capacity. Save the returned token;
    use the pinned base/input heads and workload hash.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - claim
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
        type:
        - string
        - 'null'
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
    - ttl
    additionalProperties: false
cli:
  path:
  - tasks
  - claim
  aliases:
  - - claim
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
    ttl:
    - --ttl
  defaults:
    operation: claim
    database: null
    repo: null
    scope: workspace
    task: null
    ttl: 900
run:
  artifact: scripts/workflow.lock.json
---

# Tasks claim

Atomically lease ready work within capacity. Save the returned token; use the pinned base/input heads and workload hash.

Invoke `.tkstack/tkstack skills sdlc -- tasks claim --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
