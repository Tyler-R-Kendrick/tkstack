---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_issue
  description: Record an unexpected finding and pause affected tasks plus descendants.
    Supply a JSON object via --issue; classify ordinary implementation defects accurately.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - issue
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
      issue:
        type: object
        properties:
          id:
            type: string
            minLength: 1
          kind:
            type: string
            enum:
            - requirement
            - architecture
            - environment
            - implementation
          observation:
            type: string
            minLength: 1
          tasks:
            type: array
            items:
              type: string
              minLength: 1
          requirements:
            type: array
            items:
              type: string
              minLength: 1
          evidence:
            type: array
            items:
              type: string
              minLength: 1
            minItems: 1
        required:
        - id
        - kind
        - observation
        - tasks
        - requirements
        - evidence
        additionalProperties: false
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - issue
    additionalProperties: false
cli:
  path:
  - tasks
  - issue
  aliases:
  - - issue
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
    issue:
    - --issue
  defaults:
    operation: issue
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks issue

Record an unexpected finding and pause affected tasks plus descendants. Supply a JSON object via --issue; classify ordinary implementation defects accurately.

Invoke `.tkstack/tkstack skills sdlc -- tasks issue --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
