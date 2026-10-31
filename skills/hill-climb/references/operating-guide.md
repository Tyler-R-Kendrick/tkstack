# Hill-climb

Improve a real outcome through attributable experiments. Keep a trustworthy
incumbent, test one hypothesis, measure, then keep or revert. Inspection,
optimistic narration, and a favorable training score are not measured wins.

This independently written workflow combines Pstack's scientific iteration
with Anthropic's eval hill-climbing discipline. See [sources and differences](../references/sources.md).
Creating or installing this skill does not start experiments or spend API budget.

## 1. Ground the objective

Inspect the target, architecture, realistic workload, and existing evaluation
before designing another harness. Reproduce the user's complaint. If the
workload cannot reproduce it, fix the reproduction first. Distinguish a one-off
bug fix from a sustained optimization loop.

Record the objective, direction, scope of permitted edits, off-limits files,
regression gates, practical improvement threshold, and target. Include quality,
cost, latency, and functionality constraints where relevant. Use the current
user instructions and standing authorization; ask only for material information
or spending scope that is missing. Propose concrete defaults for local reversible
work rather than introducing an approval ritual at every round.

Write a bounded plan before editing: maximum rounds, wall-clock/cost ceiling,
minimum attempts if requested, plateau patience, and check-in cadence. A user
target and attempt floor take precedence; neither overrides correctness or
budget. Without supplied numbers, default to at most five local rounds, a
plateau review after three rejected attempts, and no new paid calls without an
established budget. Do not silently start an unbounded overnight optimizer.

Use [the plan template](../templates/plan.json) as a starting contract. Placeholder
hashes are intentionally not executable evidence. Record a resumable run under
an ignored project directory such as `.tkstack/hill-climb/<run>/`; avoid home
configuration and plugin caches. Put a concise plan and summary in the task
artifacts when they need review.

## 2. Prove and freeze the measurement

Before spending optimization rounds:

1. Prove the runner exercises the actual mechanism being changed. Compare a
   known good/bad or enabled/disabled control; check meaningful work and error
   counts. A faster runner that omits work is not an improvement.
2. Audit representative failure outputs and the grader's reasoning against
   the requirement. Separate harness errors, bad expected values, and real
   product failures. Fix a broken grader before freezing a new baseline;
   never edit it mid-climb to rescue a candidate.
3. Repeat the unchanged baseline. Record sample count, realistic cache/warmup
   conditions, noise, and available headroom. If the smallest actionable gain
   is below noise, improve measurement or report that the climb cannot resolve
   it. For stochastic generated indexes/assets, repeat builds as well as reads;
   rescoring one build does not measure build variance.
4. Freeze runner, dependency lockfiles, cases/splits, grader, metric definition,
   model/judge configuration, and relevant rubric snapshots by content hash.
   Include the current scoped `unslop` snapshot when it is a grader. These
   hashes detect listed changes; they are not an execution sandbox or proof of
   dependency/runtime identity. Record interpreter, provider and environment
   separately where they can affect results.
5. Capture the baseline with a green meaningful regression gate. Recompute
   aggregates from per-case data. Record full traces, actual served model,
   input/output/cache usage, retry costs, and grades from the **same calls** in
   model-based experiments. Do not rerun to collect a nicer transcript.

Keep train cases for diagnosis, a separate selection/validation set for round
decisions, and a final untouched confirmation set when data permits. Split
randomly with a recorded seed, stratify by workload class, and keep related
examples together to avoid leakage. Never select training examples solely for
their low baseline scores. Anything repeatedly used to choose edits is a
selection set, even if a tool calls it “test.” Hide confirmation outputs from
the proposer until the winner is fixed. With too little independent data,
report exploratory results without claiming held-out improvement.

## 3. Run attributable rounds

Read the decision log before each attempt. Diagnose actual training failures
and traces, not just aggregate scores. Form a mechanism-based hypothesis with
the expected effect and a falsifier: “defer index loading off startup because
the trace shows it blocking first paint,” rather than “try caching.”

Change one coherent lever per round. Keep the incumbent and rejected patches.
Use isolated worktrees for independent candidates; when delegation is permitted
and useful, give each agent a narrow hypothesis and separate worktree. In an
active `sdlc` workflow, use its leased DAG, verified COW/sparse worktree and cache
rules, BDD/contracts, and independent adversarial review. Shared caches must
not introduce mutable cross-branch state or contaminate cold-cache benchmarks.
If COW is unavailable, report it and follow SDLC's explicit fallback policy.

Run the frozen measurement and regression gate. Supervise long commands through
the harness's supported background/session mechanism; remain available for
user steering. Don't leave unawaited calls that die when the session exits.
Independent candidates may run concurrently only when they do not contend for
the resource being measured; otherwise serialize measurement or measure the
intended contention explicitly. Compare every parallel candidate against the
same incumbent; rebase and remeasure combinations before accepting them.

Accept only if the target improves beyond both noise and the actionable
threshold, guardrails hold, the predicted mechanism is supported, and the
meaningful regression gate stays green. A benchmark win that breaks behavior,
invents facts, omits work, or worsens a required visual state is rejected.
A useful simplification at equivalent performance may be retained only when
explicitly included in the objective; report it as simplification, not a speed win.

For structured measurements, the optional [comparison helper](../references/measurement.md)
checks paired cases, evidence hashes, frozen files, gates, and improvement
thresholds. It does not execute the runner, judge semantics, edit files, or
commit. Record its result together with the real experiment evidence.

Revert rejected edits in their isolated branch or with the exact inverse patch;
never reset unrelated user work. Make one incremental commit per accepted
change, staging only owned files. Retain every attempt in `decision.tsv`:

```text
id  incumbent  hypothesis  change  before  after  delta  gates  decision  evidence  note
```

Record attempts that failed to run as errors, with their costs, rather than
silently treating them as clean misses or passing retries. Do not stack
untested edits. Update a short narrative with what the evidence changed.

## 4. Audit plateaus and stop honestly

After the registered patience threshold, categorize remaining failures: product
defect, grader error, wiring error, weak/noisy signal, dataset ambiguity,
capability limit, or missing evidence. Pivot to another mechanism if cheap,
in-scope ideas remain. A suspected harness error pauses the comparison; fixing
it starts a new frozen baseline rather than rewriting old grades as progress.

Stop when the recorded target plus attempt floor is met, the budget is reached,
or a documented plateau leaves no worthwhile in-scope hypothesis. Don't relax
the threshold to declare victory, endlessly rephrase a dead prompt, or spin
past a spending ceiling. Preserve the best eligible incumbent and state what
remains unachieved. New user constraints or an evolving `unslop` catalog can
change the objective; freeze a new version and rebaseline explicitly.

## 5. Confirm, review, and deliver

Fix the winner before opening untouched confirmation cases. Run both the
original baseline and winner on the same held-out workload under matching
conditions. Confirm quality, cost/latency guardrails, and the predicted mechanism
with appropriate repeats and uncertainty estimates. A failed confirmation is
reported as such; do not tune on those cases and keep calling them untouched.
Restore the last confirmed state or leave the result as an unadopted candidate.

Review the actual final diff and relevant artifacts against the original task
requirements, not only the metric. For UI/media, compare rendered screenshots,
recordings, and full assets as appropriate; use `unslop`'s current confirmed
patterns as a quality gate. During a fixed-rubric comparison, hold its snapshot
constant and restart if a correction changes it. Preserve functionality and
accessibility while improving design. For custom skill prompt changes, retain
the `learn improve` proposal and use the configured SkillOpt adoption gate when
its real eval suite applies. This generic loop does not bypass that gate.

Deliver accepted commits and stacked PRs within the authorized scope. An active
`sdlc` workload owns final independent evidence review and PR babysitting:
address comments, keep CI green, squash roots before restacking children. Skill
creation alone does not authorize pushing or merging unrelated repository work.

Report the objective and fixed workload, original baseline versus confirmed
winner, uncertainty and sample count, quality/cost effects, attempts kept or
reverted, accepted fixes, decision-log/evidence paths, remaining gaps, and the
best untried hypothesis. If results are only exploratory or inside noise, say
so plainly. Keep this concise and link the detailed record.
