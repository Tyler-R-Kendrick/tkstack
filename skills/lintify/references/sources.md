# Sources and implementation boundaries

This is an owned authoring workflow using tkstack's deterministic-first and
bounded-concurrency principles. It complements skillify's packaging and
hookify's event enforcement. It is not a fork of an upstream lint engine.

- [ESLint custom-rule API at 9.39.1](https://github.com/eslint/eslint/blob/v9.39.1/docs/src/extend/custom-rules.md)
  establishes rule objects, metadata, visitors, and diagnostics. The example
  plugin and fixtures are original project-specific sample code.
- [Lintbook at b942c1399163ff9934dba1fc1535751aaf40124a](https://github.com/leostera/lintbook/tree/b942c1399163ff9934dba1fc1535751aaf40124a)
  separates Markdown authoring, Datafox queries, deterministic compilation,
  and model-free checking. The minimal query follows its README format.
  The checked workspace references a sibling Datafox checkout; no stable GitHub
  release was returned by `releases/latest` during research. Do not promise a
  standalone source build or claim native validation without a real binary.
- [GPTLint rule spec at f8bd578f2aee046b8aa6b887cfcda03c25803dde](https://github.com/gptlint/gptlint/blob/f8bd578f2aee046b8aa6b887cfcda03c25803dde/docs/pages/extend/rule-spec.md),
  [config](https://github.com/gptlint/gptlint/blob/f8bd578f2aee046b8aa6b887cfcda03c25803dde/docs/pages/guide/config.mdx),
  and [CLI](https://github.com/gptlint/gptlint/blob/f8bd578f2aee046b8aa6b887cfcda03c25803dde/docs/pages/guide/cli.md)
  establish Markdown frontmatter/examples, `ruleFiles`, and configuration/dry-run
  boundaries for 1.6.0. Its model-based checking remains probabilistic.

Other engines in the selection table are alternatives to investigate when the
project already uses them, not implemented native adapters in this package.
Examples and the scaffolder do not install a CLI, enable a rule, register a hook,
or call a model. Native execution and semantic efficacy are separate evidence.
