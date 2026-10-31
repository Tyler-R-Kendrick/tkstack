---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_recover
  description: Coordinator releases a stopped task after retained quiescence evidence.
    A live worker must quiesce; expiry alone never reassigns a worktree.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - recover
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
      reason:
        type: string
        minLength: 1
      evidence:
        type: array
        items:
          type: string
          minLength: 1
        minItems: 1
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - task
    - reason
    - evidence
    additionalProperties: false
cli:
  path:
  - tasks
  - recover
  aliases:
  - - recover
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
    reason:
    - --reason
    evidence:
    - --evidence
  defaults:
    operation: recover
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks recover

Coordinator releases a stopped task after retained quiescence evidence. A live worker must quiesce; expiry alone never reassigns a worktree.

Invoke `.tkstack/tkstack skills sdlc -- tasks recover --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
