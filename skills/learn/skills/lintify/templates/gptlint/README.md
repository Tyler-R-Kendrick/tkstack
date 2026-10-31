# Semantic Markdown rule example

This is an advisory GPTLint 1.6.0 source-format example. It requires the actual
CLI and an explicitly selected supported provider/model for real judgment.
Scaffolding does not spend model budget or activate a rule in another project.

Install the pinned dependency from its lock, then invoke the local binary
through npm scripts (no global installation is needed):

```sh
npm ci --ignore-scripts --omit=optional --no-audit --no-fund
npm run inspect
npm run estimate
```

Inspect/redact config output locally because credential fields may be included.
These commands establish parsing/discovery or a mocked estimate, not detection.
For a real run, supply the selected model/provider and budget using actual native
options. Repeat uncached good/bad/exception cases and inspect the diagnostics.
The config enables only this sample rule; it does not import recommended rules.

GPTLint's CLI uses a lint-error collection for its final exit decision. Do not
assume `level: warn` guarantees exit zero. Verify the observed behavior before
using it as a CI gate; this semantic example remains advisory until evaluated.
