# Sources and deliberate adaptations

Reviewed 2026-10-29 (America/Chicago).

- [Pstack Hillclimb playbook, cursor/plugins at 4dd1d05](https://github.com/cursor/plugins/blob/4dd1d05818d19792e7cd6e818f1667f95f7e1dbe/pstack/skills/poteto-mode/playbooks/hillclimb.md)
  (blob `e9cf267908a9737236b3a8a8a5a99fe9066f7554`): ground the
  workload, prove and freeze the metric, one hypothesis/measurement, keep or
  revert, decision log, accepted commits, pivot past an initial plateau.
- [Anthropic eval hill-climbing, anthropics/skills at ca45fc4](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/claude-api/shared/evals/eval-hillclimb.md):
  sensitivity and wiring checks, baseline noise, per-call transcripts/model/usage,
  failure inspection, reproducible splits, bounded iterations, explicit held-out
  result and honest uncertainty. This is the published source for Claude Code's
  `/claude-api hillclimb`, not a guessed proprietary prompt.
- [Anthropic cost hill-climbing at the same revision](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/claude-api/shared/evals/cost-hillclimb.md):
  quality band plus cost margin plus observed mechanism; fixed pricing basis,
  real cache/retry accounting, model/effort/caching levers before blind prose
  trimming, and final joint confirmation. A repeatedly consulted “test” set is
  a selection set, not an untouched final holdout.
- [Anthropic's explanation of the shipped commands](https://claude.dev/blog/automating-eval-design-and-hillclimbing/)
  provides the command context; the implementation above is based on the actual
  public guides rather than only the article.

The pinned `poteto/plugins` snapshot in this dotfiles repository predates that
new playbook. It remains byte-identical. This personal package adds the workflow
without changing Pstack's revision or replacing its other playbooks.

Adaptations: no fixed provider/model role, no harness-specific question tool,
no mandatory repeated approval where the user has already authorized the work,
and no automatic background paid loop. A bounded local default is available.
Parallel agent work is conditional on task authorization and harness capability;
independent candidates never share a writable working tree. The workflow also
extends to non-model code and media with domain-appropriate real measurements.

The split discipline is intentionally stronger than repeatedly selecting the
winner on a set called “test.” Training supports diagnosis, validation supports
selection, and untouched confirmation supports the final claim. With limited
data the skill permits exploratory work but restricts its claims. The offline
helper checks supplied evidence and uses an approximate paired interval; it is
not Anthropic's runner/report viewer, a full optimizer, or a universal statistician.
