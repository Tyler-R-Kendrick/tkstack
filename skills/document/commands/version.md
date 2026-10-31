---
schema: tkstack.command/v1
tool:
  type: function
  name: version
  description: Show the package name and declared version without execution.
  strict: true
  parameters:
    type: object
    properties: {}
    required: []
    additionalProperties: false
cli:
  path:
  - version
run:
  builtin: version
---

# Version

Use version or --version. Returns metadata.version from SKILL.md; a workflow without a declared skill version reports unversioned. Discovery never runs a workflow or initializes state.
