# Measured improvement loops

Use `/hill-climb <objective>` or `$hill-climb` for sustained improvement of a
measurable outcome. The canonical package is
[`skills/hill-climb`](../skills/hill-climb/SKILL.md), with a bounded plan template,
measurement contract, source notes, and an optional offline comparison helper.
It is directly user-invoked or used as a subworkflow by SDLC for qualifying
feature work. It installs into every selected harness; the default profile
selects Codex, Claude Code, and Cursor. Restart the
harness session to discover it. Installation does not start a run.

For a task that needs competing implementations or a revised evaluator, use
[Git-backed experiments](../skills/hill-climb/references/git-experiments.md) and
the [task harness brief](../skills/hill-climb/templates/task-harness.json).
The brief records the real integration targets, quality rubric, candidate
revisions, budget, feedback, and retention needs. It is an agent planning aid,
not an executable workflow. Select only the language runtimes and native checks
needed by the task and its changed boundaries.

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
Checkout-level grades live in [`evals/repo-quality`](../evals/repo-quality/)
([Repository quality](../evals/README.md)). That promptfoo rubric is not this
skill's JSONL comparison helper and does not adopt a patch.

Independent candidates can use separate worktrees and authorized subagents.
Concurrent timing measurements must not contaminate one another. An explicitly
active `sdlc` workflow owns COW/sparse isolation, BDD/contract testing, evidence,
independent final review, incremental commits, stacked PRs and babysitting.
This skill does not introduce permission to push or merge unrelated work.

Feedback can reveal a defect in the feature, the harness, or both. An
evaluator change is calibrated against labeled good and defective examples,
then both incumbent and challenger are regraded under the same revised
contract. Changes to agent instructions, skills, context, or workflow need
fresh matched trials; rescoring existing outputs does not establish that the
revised workflow produces better work. Keep earlier decisions and evaluator
revisions so the evidence remains auditable.

Git branches identify distinct hypotheses. The trial records the exact commit
and tree, and repeats use clean inputs at that same revision. When equivalent
trees share a measurement, decisions retain the commit that actually ran and
label the reuse. Experiment refs,
worktrees, and evidence belong outside the developer's checkout. Git worktrees
share objects but do not guarantee filesystem copy-on-write or isolate an
untrusted process. Preserve the necessary objects or a verified bundle when
source replay is required; deleting a branch does not immediately reclaim
all of its objects.

The `native experiment` command can coordinate a scoped local Git experiment.
It freezes each arm, records local trial reservations and receipts, compares
paired evidence, and advances an eligible private integration ref. Its local
runner executes trusted commands with host privileges. It hashes declared
case files, the evaluator, its direct executable or trusted interpreter, and
declared dependencies. The included native test adapter requires its configuration
and JSON parser to be declared and frozen. An optional separate quality judge
can supply numeric and qualitative criteria alongside the native test gate.
The evaluator must attest the case digest. Evaluator
revisions require calibration runs on labeled references. A default 1800-second
experiment deadline limits trial dispatch and execution. Provider spending
controls, protecting confirmation data from host processes, and external
sandboxes require separate integration.
The [Git experiment guide](../skills/hill-climb/references/git-experiments.md)
documents the request format and recovery limits, including bounded scripted
proposals, host-agent handoff, preallocated parallel trials, and an optional
Harbor separate-verifier backend and bounded local GEPA search. The optional
[MAF YAML workflow](../skills/hill-climb/workflows/experiment-cycle/README.md)
runs a bounded sequence of those requests with its own Python and .NET runtime
prerequisites.

The private Git store verifies ownership and separation from registered source
worktrees, disables hooks, and rejects configured external filter drivers during
managed checkout and freezing. A worktree is not a sandbox against another
process with the same privileges.

Lean checks unbounded budget arithmetic, with finite correspondence cases
against SQLite. The bounded controller model checks its declared transitions
and assumptions.
Optional TLA+ and TLC specifications exercise reservation and guarded promotion
models, including weakened configurations that produce counterexamples. The
[formal guide](../skills/hill-climb/formal/README.md) records the checker,
assumptions, and scope; these checks do not prove the implementation or remote
provider behavior. The local runner checks a monotonic deadline after Git export
and caps command execution to the remaining interval. Git export has its own
subprocess timeout.

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

The ledger can enforce one claim for each frozen selection assignment when
the controller supplies the candidate tree, case and repetition identity.
Nondeterministic comparisons require repeated baseline observations for every
case and a positive declared noise floor. Regrading binds submitted source and
case bytes separately from grading receipts, which may legitimately change.
