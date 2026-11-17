---
schema: tkstack.command/v1
tool:
  type: function
  name: help
  description: Generate and render a read-only command manual.
  strict: true
  parameters:
    type: object
    properties:
      topic:
        type:
        - string
        - 'null'
        description: Command path, or null for the package manual.
      format:
        type: string
        enum:
        - text
        - man
        description: Fixed console text or generated man(1) source.
    required:
    - topic
    - format
    additionalProperties: false
cli:
  path:
  - help
  positionals:
  - topic
  defaults:
    topic: null
    format: text
  flags:
    format:
    - --format
run:
  builtin: help
---

# Help

Use help [command ...] or <command> --help. Default text uses fixed rendering. Use help --format man for generated man(1) roff source. No workflow, model, pager, or state initialization runs.
