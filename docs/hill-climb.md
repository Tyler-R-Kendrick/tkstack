# Measured improvement loops

Use `/hill-climb <objective>` or `$hill-climb` for sustained improvement of a
measurable outcome. The canonical package is
[`skills/hill-climb`](../skills/hill-climb/SKILL.md), with a bounded plan template,
measurement contract, source notes, and an optional offline comparison helper.
It is user-invoked and installs in Codex, Claude Code, and Cursor; restart the
harness session to discover it. Installation does not start a run.

The workflow combines Pstack's [newer Hillclimb playbook](https://github.com/cursor/plugins/blob/4dd1d05818d19792e7cd6e818f1667f95f7e1dbe/pstack/skills/poteto-mode/playbooks/hillclimb.md)
with Anthropic's published [`/claude-api hillclimb` guide](https://github.com/anthropics/skills/blob/ca45fc496a3436251f191354091d557da31c15b5/skills/claude-api/shared/evals/eval-hillclimb.md)
and cost-specific guidance. The pinned Pstack snapshot predates its playbook;
it was preserved rather than silently updated. See
[source details and adaptations](../skills/hill-climb/references/sources.md).

The loop grounds the real workload, proves measurement sensitivity, repeats
the unchanged baseline, freezes evaluation inputs, and tests one mechanism at
a time. It keeps only changes that clear noise and practical improvement
thresholds while meaningful behavior and quality gates stay green. It logs
all attempts, reverts rejected changes, reviews plateaus, respects time/cost
budgets, and confirms the fixed winner on untouched cases. A repeatedly used
selection set is never called an untouched final test.

Examples:

```text
/hill-climb reduce cold startup latency below 100ms while preserving the contracts
/hill-climb improve this skill's held-out task success within a $10 eval budget
/hill-climb improve this landing page against the brief, using unslop as a quality gate
```

Visual examples require actual rendering and artifact inspection; source-only
or keyword scores cannot establish a design win. A fixed unslop rubric snapshot
is hashed with the run; new user corrections change the rubric and require a
fresh comparison. For skill-prompt changes, the configured `learn improve` and
SkillOpt adoption gate still applies when its real suite is available.

Independent candidates can use separate worktrees and authorized subagents.
Concurrent timing measurements must not contaminate one another. An explicitly
active `sdlc` workflow owns COW/sparse isolation, BDD/contract testing, evidence,
independent final review, incremental commits, stacked PRs and babysitting.
This skill does not introduce permission to push or merge unrelated work.

For an actual structured run, copy and complete
[the plan template](../skills/hill-climb/templates/plan.json). The helper compares
existing JSONL results with hashed trace receipts:

```sh
python3 skills/hill-climb/scripts/hill_climb.py \
  --plan /path/to/run/plan.json \
  --baseline /path/to/run/baseline.jsonl \
  --candidate /path/to/run/round-1.jsonl --split selection
```

It checks frozen listed files, disjoint cases, complete repetitions, finite
measurements, regression gates, equivalent work, paired noise, and guardrails.
It never executes commands or adopts a patch. Budget/round enforcement, actual
trace inspection, and untouched holdout isolation belong to the workflow and
reviewer. See [measurement details](../skills/hill-climb/references/measurement.md).

Tests use synthetic measurements to verify comparison and evidence boundaries.
No paid experiments, measured application improvement, or held-out model
performance gain is claimed from creating this skill.
