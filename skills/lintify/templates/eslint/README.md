# Native ESLint example

This is a syntactic example, not an activated project policy. Adapt the rule,
scope, and cases to the actual requirement. It matches direct identifiers named
`auditEvent`, including locally shadowed identifiers; it does not resolve binding
identity, inspect method calls, or judge whether a reason is truthful.

Install the pinned direct dependency with the project's package manager and
retain its lock. Then run:

```sh
npm test
npm run lint:good
npm run lint:bad
```

The bad fixture must return a finding. The example config selects only fixture
JavaScript and does not load other project configs. For a production rule, merge
it at the actual config owner and verify real target discovery/ignore behavior.
There is no autofix because inventing a justification changes the meaning.
