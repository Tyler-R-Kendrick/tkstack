# Evolution tool selection

Evaluated 2026-10-29 (America/Chicago) for the custom `learn` and `sdlc` skills.
The goal is to improve instructions while preserving correction provenance,
harness independence, workflow obligations, helper behavior, and reviewable
changes. This is an architectural comparison using primary documentation, not
a four-tool performance benchmark.

| Tool | Appropriate use | Fit for these two skills |
| --- | --- | --- |
| [SkillOpt / SkillOpt-Sleep](https://github.com/microsoft/SkillOpt) | Bounded text edits driven by scored attempts, separate validation, rejection history, and staged promotion | **Historical selection.** Its task parser is retained; separate model and harness execution is no longer offered. Its Python Sleep engine needs no research-package dependencies. |
| [WikiSkill](https://github.com/ashutoshsinghpr7/wikiskill) | Accumulate raw evidence, maintain a wiki of patterns, and distill/gate skills within a domain workspace | Useful foundation for `learn`'s evidence/knowledge/steering separation and already installed. Its broader wiki workspace and task-validator loop add less value for revising two existing packaged workflows. The pinned implementation is independent of the paper authors. |
| [Microsoft Vally](https://microsoft.github.io/vally/) | Extensible trajectory evaluation with custom executors, graders, isolated environments, and reports | A strong future choice for behavioral evaluation across harnesses. Its documented core evaluates rather than proposes bounded revisions; a separate optimizer and native executor integration are still needed for this task. |
| [Microsoft Waza](https://github.com/microsoft/waza/tree/v0.39.0) | Repository/CLI/MCP workflow scenarios, artifact and behavior graders, adversarial checks, readiness/coverage and CI regression gates | Especially useful for deeper SDLC workflow evaluation. The published Go CLI is heavier than the dependency-free Sleep component, and its evaluation/authoring/token tools are not a substitute for a general validation-gated revision optimizer. |

Sources include the pinned
[Sleep guide](../vendor/skillopt/docs/sleep/README.md),
[multi-skill staging contract](../vendor/skillopt/docs/sleep/multi-skill-staging.md),
[WikiSkill README](../vendor/wikiskill/README.md),
[Vally executor documentation](https://microsoft.github.io/vally/guides/writing-custom-executors/),
[Microsoft's Vally integration](https://github.com/microsoft/GitHub-Copilot-for-Azure/blob/main/.github/skills/vally-eval/SKILL.md),
and Waza's released README. A direct `microsoft/vally` repository lookup returned
404 through the connector; Vally was assessed through its official hosted docs
and Microsoft's documented `@microsoft/vally-cli` consumers. Waza and Vally
were not installed or executed for this comparison.

## Current host-bound integration

The SkillOpt task parser is used for reviewed authored case files. Home
dotfiles setup fetches the current source and the driver records the actual
source revision used for each run; the bundled snapshot is an offline reference.
[`evolve.py`](../skills/learn/scripts/evolve.py) validates and pins the skill,
case bytes and source revision, then returns readiness for the invoking agent.
It does not run an optimizer, choose a model, launch a separate agent harness,
or automatically adopt changes.

```sh
python3 skills/learn/scripts/evolve.py learn --dry-run
python3 skills/learn/scripts/evolve.py constrain
```

The invoking agent carries out semantic work in its current conversation.
Visible examples and labels are not independent holdouts. If a host cannot
supply a genuinely independent confirmation without another agent or model,
report the evidence gap. The earlier comparison and trial below are historical,
not current instructions to launch a separate backend.

## Recorded initial trial

This is the historical learn 0.1.0 decision trial, before the explicit
Grok-inspired improvement/report modes added in learn 0.2.0. Its recorded hashes
remain attached to that original snapshot. They are not relabeled as evidence
for later skill bytes; a new run needs a new input identity and actual results.

The [recorded result](../evals/results/2026-10-29.json) covers eight distinct
fresh-context model calls, four per skill: one training decision, two validation
decisions, and one final test decision. These are author-created policy
regressions, explicitly marked `origin: authored`; no private transcript was
harvested or represented as a real-session benchmark.

| Skill | Training | Validation baseline → retained final | Final test | Revision decision |
| --- | --- | --- | --- | --- |
| learn | 1/1 | 2/2 → 2/2 | 1/1 | No accepted edit |
| sdlc | 1/1 | 2/2 → 2/2 | 1/1 | No accepted edit |

All training decisions passed, so the engine's failure-driven reflector had
nothing to revise. The final gate reported `reject` for an unchanged 1.0 → 1.0
score. Preserving the current instruction is the correct result; equality is
not an improvement. There was no accepted patch, memory change, or steering
ledger change.

An initial scorer probe exposed that upstream `exact_score` uses substring
matching. A single-letter reference could match a pending marker and publish a
misleading score. The retained fixtures use anchored regex action graders,
which reject pending markers, embedded labels, empty replies, and extra prose.
The stricter run reused only observed replies whose exported prompts matched
byte for byte. The earlier substring-scored artifacts are excluded from the
recorded result. Regression tests guard this integration boundary.

This trial demonstrates instruction-consistent decisions and a working
fail-closed integration. It does not measure real tool execution, long-running
PR babysitting, screenshot quality, production contracts, statistical lift, or
transfer to another model/harness. Helper tests separately exercise actual Git,
files, leases, and evidence gates. Deeper evolution needs observed failures,
real task validators, negative controls, multiple trials, and new evaluation
cases; do not repeatedly tune against these fixed tests and call them unseen.

## All-owned-skill normalization trial

The 2026-10-31 normalization extended the existing driver to all 19 owned
skills, with reviewed authored train/validation/test scenarios for each. The
[current-source results](../evals/results/2026-10-31-owned-skills.json) retain
exact skill/task hashes and actual strict-gate decisions. The handoff used 65
genuine fresh-context evaluator calls across 59 distinct authored scenarios;
two compiler skills were rerun after final index changes. No mock or inline
answer was substituted, and full prompt/reply/agent provenance stays private
under `.tkstack/`.

All decisions passed. Gates correctly rejected every 1.0 to 1.0 tie and
proposed/adopted no extra instruction edit. Engineering normalization changed
all packages separately and is covered by actual compiled/native behavior
checks. This is not a general model-quality improvement claim. Fixed-case reuse
and relay/cache usage estimates remain explicit limitations. See
[per-skill automation, tests and boundaries](normalization.md).
