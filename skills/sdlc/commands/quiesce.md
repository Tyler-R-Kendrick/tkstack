---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_quiesce
  description: Acknowledge stopped worktree writes before an affected graph revision.
    Keeps the blocked record for review.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - quiesce
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
      reason:
        type: string
        minLength: 1
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - task
    - token
    - reason
    additionalProperties: false
cli:
  path:
  - tasks
  - quiesce
  aliases:
  - - quiesce
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
    reason:
    - --reason
  defaults:
    operation: quiesce
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks quiesce

Acknowledge stopped worktree writes before an affected graph revision. Keeps the blocked record for review.

Invoke `.tkstack/tkstack skills sdlc -- tasks quiesce --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
