---
schema: tkstack.command/v1
tool:
  type: function
  name: sdlc_tasks_revise
  description: Coordinator applies an explicit authorized amendment using --revision
    JSON. Requires expected revision, every prior requirement disposition, resolved
    issue IDs, and ADR records for architecture resolutions.
  strict: true
  parameters:
    type: object
    properties:
      operation:
        type: string
        enum:
        - revise
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
      revision:
        type: object
        properties:
          expected_revision:
            type: integer
            minimum: 1
          graph:
            type: string
            minLength: 1
          rationale:
            type: string
            minLength: 1
          authorization:
            type: string
            minLength: 1
          requirements:
            type: array
            items:
              type: object
              properties:
                id:
                  type: string
                  minLength: 1
                status:
                  type: string
                  enum:
                  - unchanged
                  - changed
                  - withdrawn
                reason:
                  type: string
                  minLength: 1
              required:
              - id
              - status
              - reason
              additionalProperties: false
          resolves:
            type: array
            items:
              type: string
              minLength: 1
          adrs:
            type: array
            items:
              type: object
              properties:
                path:
                  type: string
                  minLength: 1
                decision:
                  type: string
                  minLength: 1
              required:
              - path
              - decision
              additionalProperties: false
        required:
        - expected_revision
        - graph
        - rationale
        - authorization
        - requirements
        - resolves
        - adrs
        additionalProperties: false
    required:
    - operation
    - run
    - actor
    - database
    - repo
    - scope
    - revision
    additionalProperties: false
cli:
  path:
  - tasks
  - revise
  aliases:
  - - revise
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
    revision:
    - --revision
  defaults:
    operation: revise
    database: null
    repo: null
    scope: workspace
run:
  artifact: scripts/workflow.lock.json
---

# Tasks revise

Coordinator applies an explicit authorized amendment using --revision JSON. Requires expected revision, every prior requirement disposition, resolved issue IDs, and ADR records for architecture resolutions.

Invoke `.tkstack/tkstack skills sdlc -- tasks revise --run <run> --actor <owner> ...`.
[Task coordination](../references/durable-task-graph.md) defines storage, errors, lease ownership, revision rules, and end-to-end examples. The frontmatter is the exact tool/flag contract.
