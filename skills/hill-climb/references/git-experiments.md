# Git-backed task experiments

Use this procedure when a measured task needs competing changes, or when
feedback shows that its evaluation or agent workflow needs improvement. The
[task harness brief](../templates/task-harness.json) is a starting document for
the agent and reviewer. It is not an executable workflow or an input to the
existing comparison helper. Replace its placeholders with facts from the
current task; omit fields that are not applicable. Keep the actual numeric
comparison contract in [plan.json](../templates/plan.json) when using the
existing helper.

## Scope and instrument

Inspect the real integration boundary and choose only the native targets
needed to exercise this change, plus checks required by the project. List the
editable paths, immutable starting revision, target identifiers, and why each
target is required. A second language or service belongs in the experiment
when the changed contract crosses that boundary. Its mere presence in the
repository is not a reason to run it. Record required tool and environment
versions where available and a truthful reason when they cannot be pinned.

Define the user's outcome, mandatory behavior, a measurable quality change,
resource limits, and stop rule. For qualitative quality, give observable anchors
and the evidence needed to apply them. Include an insufficient-evidence outcome.
Prove that the instrument separates a known good outcome from a known defect;
inspect the actual output. Establish the incumbent and measure relevant noise
before trying a challenger. Label any unsupported or too-small comparison
exploratory rather than claiming a confirmed win.

Start with an incumbent and one candidate when that is enough to answer the
question. Reserve a broader search for evidence that justifies it. All
proposer, trial, retry, judge, and nested-work usage belongs to the same task
budget. Record the fixed per-call limit and observed usage where available.
Do not assume a provider can enforce a strict token or currency ceiling unless
its adapter actually does so. Account for unknown execution after a lost
response; retry only when the original outcome and available budget allow it.

## Record each candidate in Git

Resolve the baseline to a full commit ID and record the repository and tree.
Use a private experiment repository outside the developer's checkout. Create
one branch for each distinct hypothesis, rooted at the same applicable
incumbent. Give each concurrent writer a separate worktree and owned paths.
If the user asks to include working-copy changes, first capture and identify an
explicit baseline snapshot. Preserve unrelated staged, unstaged, and untracked
work.

A linked worktree shares Git objects and refs. It has its own working files,
HEAD, and index. Git does not promise filesystem copy-on-write for those files
or their build outputs. It is not a security boundary. Keep authoritative
evaluators and final cases outside agent-writable locations, and run untrusted
code with the host's actual isolation mechanism.

Freeze each measured candidate to its commit and tree ID. Repetitions of that
candidate use the same IDs and clean trial inputs; they do not create new
branches. Retain its hypothesis, contract and evaluator revisions, runner and
environment, budget, all assigned attempts, evidence locations, and decision.
Record infrastructure errors, timeouts, and missing evidence separately.
A failed launch is not a failed product scenario, and omitted attempts are not
a successful measurement.

Each selection case and repetition is claimed once per candidate tree,
comparison side, contract revision, and integration generation. Equivalent
commits with the same tree reuse the original settled evidence. An interrupted
dispatched trial remains claimed until reconciled. If you need more samples,
revise the frozen evaluation's repetition count and rebaseline the comparison;
do not rerun an existing assignment under a new key and select the better score.
Decision rows record the requested candidate together with the run key, actual
measured commit and tree, and whether the result is direct or reused for an
equivalent tree. Regrading reconstructs the measured source commit. The handoff
returns the candidate provenance after revalidating the retained decision.

Select on the frozen contract and recorded evidence. A candidate must satisfy
mandatory checks before any quality improvement can count. Recheck the exact
prospective integration tree if merging, rebasing, conflict resolution, or a
moved target changes what would be delivered. Follow the repository's authorized
integration workflow; a measured result does not itself grant publication or
merge authority. Keep task harness changes out of product history unless they
are deliberately adopted there.

After writers have stopped, preserve the decision and evidence. If future
source replay is required, retain the required Git objects or create and
restore-check a bundle with its base prerequisites before deleting a branch.
A commit ID alone does not retain its objects. Remove only controller-owned,
clean worktrees and the expected branch tip. Investigate active leases, locks,
changed tips, and dirty paths instead of force-cleaning a developer checkout.
Branch deletion removes a name, not necessarily the underlying objects; Git
retention and shared references determine when storage can be reclaimed.

Before delivering a promoted private champion through an SDLC stack, use the
[verified Git handoff](git-handoff.md) to stage its exact evaluated tree in
a clean, owned delivery worktree. Re-evaluate if integration changes that tree.

## Improve the harness from feedback

A feature change and a measurement change answer different questions. Hold the
harness fixed while comparing features. When feedback reveals a missing or
misleading criterion, retain the original observation, your interpretation,
a concrete distinguishing scenario, and the proposed change to policy, rubric,
metric, selected skills, or workflow. Keep uncertainty explicit and ask for
clarification only if it prevents a meaningful interpretation.

Qualify a revised evaluator against independently labeled good and defective
examples. Regrade saved incumbent and challenger outputs under both the old and
new evaluator when the artifacts contain sufficient evidence:

| Submission | Old evaluator | Proposed evaluator |
| --- | --- | --- |
| Incumbent | Prior judgment | Does the reported defect become visible? |
| Challenger | Existing regressions | Does the revision satisfy the new criterion? |

If the required artifact is missing, rerun both with the needed instrumentation.
If the feedback changes the accepted outcome, create a new contract revision
and rebaseline. Never compare a previous score under one contract with a new
score under another as a feature gain. A weaker evaluator cannot promote itself
because it gives larger numbers.

Changes to instructions, context, tools, selected skills, or agent routing
require fresh matched coding trials from the same starting revision under the
same relevant budget. Regrading old outputs alone cannot show that a workflow
produces better work. A combined workflow and evaluator change needs both
fresh trials and evaluator calibration. Preserve the old harness and decision
record so that the new result can be audited or rolled back.

Use development cases to diagnose and propose. Fix the finalist before running
confirmation against evaluator-held cases. Repeatedly using a case to choose
candidates makes it selection data. Blinded ordering and independent human
labels can help calibrate subjective judgments; an unsupported model rating or
confidence is not evidence of user agreement.

## Reuse what is demonstrated

A reusable template can reduce future harness construction time. First verify it
on the relevant task and preserve its version and assumptions. Promote a
template beyond that task only after comparing it with the current template on
unseen tasks inside its claimed scope and matched overall budgets. Measure
authoring effort, defect detection, false rejection, final quality, and spend
when those measurements are meaningful. A result from one language or task
family does not establish results for every other one.

The optional numeric comparison helper checks the receipts and frozen files
specified by its own [measurement contract](measurement.md). The agent and
reviewer still own semantic grading, task selection, evidence inspection, and
decisions about updating the harness. Use the native task runner and isolation
available for the actual project; the existence of this document or a template
does not execute an agent, provision Harbor, invoke an optimizer, or prove an
improvement.

## Local experiment command

The compiled skill exposes `native experiment --request PATH`. To start
from the supplied brief template, give it a JSON request such as:

```json
{
  "action": "draft", "source": "/path/to/project",
  "goal": "Preserve valid entries after a validation error",
  "paths": ["web/form/"], "target": "web.form.interaction",
  "reason": "The invalid-field handler replaces valid state",
  "output": "/path/outside/project/brief.json"
}
```

The draft generator records the current Git commit unless given a full
`base` commit ID. It fills only those supplied task facts and leaves the
rubric, evaluator, budget and other placeholders for the operator. It does
not start a trial.

Other actions use a JSON object with an `action` and an absolute `root`.
The root must be absent when initialized and outside the source checkout. The
CLI runs one registered native target for the task. The trusted evaluator
prints JSON with `gates` (boolean values), `metrics` (finite numbers),
positive `work_count`, and `case_sha256` computed from the case input it
actually evaluated. An exit failure, missing output, missing evidence, or
mismatched case digest is not a successful quality result.

For example, an initial request has this shape. Replace the paths, full Git ID,
case, gates, and thresholds with real task inputs. Use the evaluator as the
executable, or put it immediately after an explicitly trusted interpreter.
Resolve and review the actual interpreter path; the example is illustrative.

```json
{
  "action": "init", "root": "/tmp/example-experiment",
  "source": "/path/to/project", "experiment": "recovery",
  "base": "<full-base-commit>", "paths": ["web/form/"],
  "target": "interaction",
  "registry": {"interaction": {"argv": ["/usr/bin/python3", "/path/to/trusted_evaluator.py", "{{case}}", "{{case_file}}"], "cwd": "."}},
  "trusted_interpreter": "/usr/bin/python3",
  "case_files": {
    "invalid-field": "/path/to/selection-case.json",
    "independent-recovery": "/path/to/confirmation-case.json"
  },
  "contract_file": "/path/to/contract.txt",
  "evaluator_file": "/path/to/trusted_evaluator.py",
  "evaluator_dependencies": ["/path/to/evaluator_fixture.json"],
  "evaluation": {
    "case": "invalid-field", "repetitions": 1,
    "required_gates": ["submit"], "candidate_only_gates": ["preserves"],
    "metric": "recovery", "direction": "higher",
    "min_gain": 1, "noise_floor": 0, "deterministic": true
  },
  "confirmation": {"cases": ["independent-recovery"], "repetitions": 1},
  "max_trials": 4, "max_tokens": 0, "max_elapsed_seconds": 1800
}
```

Invoke the same command for each action by changing the request file. Inspect
each JSON response before continuing.

| Action | Additional request fields | Effect |
| --- | --- | --- |
| `allocate` | `arm` | Return a private worktree from the frozen baseline. |
| `freeze` | `arm`, `message`, `writers_stopped: true` | Commit permitted paths and return its commit and tree. |
| `run` | `side` (`baseline` or `candidate`), `rep`, unique `run_key`, and `arm` for a candidate. Use `split: confirmation` for a selected finalist. | Reserve one trial, execute the target on the frozen tree, and retain output and accounting. |
| `compare` | `arm`, `baseline` and `candidate` arrays of run keys, unique `decision` | Save a paired comparison. Incomplete or mismatched evidence is inconclusive. |
| `select` | `decision` | Lock the eligible finalist before running configured confirmation cases. |
| `confirm` | `baseline` and `candidate` arrays of confirmation run keys | Compare the selected finalist with its baseline on the disjoint confirmation assignments. |
| `promote` | `arm`, `decision` | Revalidate the eligible evidence and advance a private integration ref with a generation and receipt ref in a Git ref transaction. |
| `handoff` | `decision`, `delivery`, `writers_stopped: true` | Revalidate the promoted result and stage its exact tree into an owned clean delivery worktree. |
| `recover` | `decision`, optional `retry: true` | Reconcile a matching promotion receipt, or retry a still-unchanged intent after rechecking its evidence. Mismatches remain unresolved. |
| `recover-run` | `run_key` | Settle a dispatched run whose complete receipt and matching output were written before interruption. |
| `retire` | `arm`, `expected` commit, `writers_stopped: true`, optional `archive` | Remove a clean private worktree and matching arm ref. An archive is restore-checked first. |
| `status` | none | Read budget, runs, events and private integration ref. |
| `feedback` | `id`, `observation`, `interpretation`, `counterexample`, `old_contract`, `new_contract`, `changes` | Retain the proposed feedback revision. Contract fields are SHA-256 digests. |
| `calibrate` | `records` | Compare supplied good/bad labels and observed judgments for diagnosis. These supplied records alone do not authorize a revision. |
| `calibration-run` | unique `run_key`, full `commit`, `case`, `case_file`, proposed `evaluator_file` and `registry`, plus `trusted_interpreter` and `evaluator_dependencies` when applicable | Run the proposed evaluator on a labeled reference submission, charging one trial to the existing budget. |
| `revise` | `feedback` ID, new `contract_file`, `evaluator_file`, `registry`, run-backed `calibration`, optional `evaluation` and `case_files` | Activate a calibrated contract revision without resetting the budget. Run the baseline and challenger again under it. |
| `regrade` | `old_spec`, `new_spec`, `old_baseline`, `old_candidate`, `new_baseline`, `new_candidate`, `evidence_root` | Check a four-cell regrade of the same retained submission and case artifacts. |
| `regrade-capture` | `capture`, `old_decision`, `new_decision` | Reconstruct Git submission snapshots, retain the case inputs, and build a four-cell matrix from settled controller receipts. |

For a stochastic metric, each case requires at least two baseline repetitions
and a positive `noise_floor`. The comparator checks gain against both that floor
and the largest observed within-case baseline standard deviation. This is a
conservative screen; it does not establish independent samples or replace a
domain-specific uncertainty analysis.

After comparing the same two Git commits before and after an evaluator revision,
capture the controller's four-cell evidence:

```json
{
  "action": "regrade-capture",
  "root": "/absolute/path/to/experiment",
  "capture": "feedback-1",
  "old_decision": "before-feedback",
  "new_decision": "after-feedback"
}
```

Call `native experiment --request` with this JSON file. The response links
`matrix.json` and the computed result under the experiment's `regrades/`
directory. The capture validates settled run receipts and frozen historical
configuration, reconstructs source snapshots from exact Git trees, and copies
case bytes retained at initialization or revision. The same source and case
must appear in both cells for each candidate. Evaluator stdout receipts and
scores may differ. Git objects and receipts must remain available when capturing.
Generated runtime outputs such as screenshots need their own retention workflow;
reconstructed source does not reproduce those outputs.

For a manual `regrade` request, each row has the usual commit, tree, contract,
evaluator, case, repetition, gates, metrics and work count. `artifacts` names
the grader's evidence, and `submission_artifacts` names separately retained
submission bytes. `case_sha256` identifies the input and `case_artifact`
points to its retained bytes. Paths are relative to `evidence_root`:

```json
{
  "artifacts": [{"path": "grades/old-result.json", "sha256": "<grade-sha256>"}],
  "submission_artifacts": [{"path": "submissions/baseline.tar", "sha256": "<submission-sha256>"}],
  "case_sha256": "<case-sha256>",
  "case_artifact": {"path": "cases/input.json", "sha256": "<case-sha256>"}
}
```

The grader receipt may change between revisions. The submission and case
receipts may use different paths only when their contents hash identically.
`matrix.json` contains a complete populated example that can be passed back
to `regrade` with `action` and `root` added.

When `confirmation` is configured, promotion requires an eligible confirmation
for the selected finalist. Selection prevents further selection trials and
edits until the comparison finishes. Each confirmation assignment can run once.
If confirmation fails, use `feedback` and `revise` with fresh confirmation
cases and the same remaining ledger budget. Previously exposed confirmation
cases are not reusable for that purpose. After a confirmed champion advances,
a further round also needs fresh confirmation cases in a revised configuration.
Case history compares identifiers and exact input digests, but cannot detect
semantic duplicates. The local setup does not hide its files from a host user
or agent.

Every selection and confirmation case must have a path in `case_files`.
The controller records each file's SHA-256 and rejects duplicate input bytes
across different case IDs. It passes the case path through the required
`{{case_file}}` argv token. An evaluator must hash the input it reads and
return that digest in `case_sha256`; the controller compares it with the
frozen input. This is an attestation by the trusted evaluator, not proof that
its test actually exercised the input.

For multiple cases specify `cases` instead of `case`, put the exact token
`{{case}}` in the target argv, and set `case` on each run. The exact token
`{{rep}}` passes its repetition number. Every declared case and repetition
must appear once on each side. Required gates apply to both sides.
`candidate_only_gates` allow a baseline defect while requiring the challenger
to fix it. Guardrails check each case as well as the aggregate.

The command cooperatively locks controller actions. Local trial execution is
serialized to prevent measurement contention. It cannot verify that an
external editor has stopped. The caller must actually stop writers before
asserting `writers_stopped`. The local runner has host filesystem and network
access and is suitable only for trusted targets. It requires `max_tokens: 0`
and does not measure or prevent model calls made inside a target. Use a separate
sandbox and a provider-aware accounting adapter for untrusted code or model
spending. The experiment-wide wall-clock deadline defaults to 1800 seconds
and can be set at initialization with a positive finite `max_elapsed_seconds`.
Run and calibration dispatch fail when it expires or the observed wall clock
moves backward. A running target is capped by the remaining time; clock
changes and descendant processes need the host's normal supervision. The
deadline does not stop external agents or provide a provider spending limit.
A lost run response before a receipt is persisted leaves its reservation
outstanding for manual reconciliation. Partially initialized, allocated or
retired workspaces can likewise need manual inspection. Submodules and Git LFS
need a materialization adapter. Git ref transactions guard concurrent updates,
but a crash may leave refs partially visible. Recovery quarantines mismatches.

The controller resolves and hashes the direct evaluator or its explicitly
trusted interpreter executable, and hashes the evaluator file. List every
additional evaluator dependency, including imported local modules, adapter
configuration, native test executable, and fixtures, in
`evaluator_dependencies` where applicable. The controller checks these
declared bytes and case inputs before and after execution. It cannot discover
undeclared dependencies or pin interpreter libraries, installed packages,
environment variables, or external services; record them separately and avoid
claiming reproducibility when they can change. Only controller-approved frozen
arm tips can run as candidates.

### Run-backed evaluator calibration

Before `revise`, use `calibration-run` to execute the proposed evaluator
on independently labeled reference commits and case files. At least two
distinct commit/input pairs are required, including expected positive and
negative examples for the same required or candidate-only gate. The
`calibration` array supplied to `revise` references the settled runs:

```json
[
  {"id": "good", "run_key": "cal-good", "gate": "preserves", "expected": true},
  {"id": "bad", "run_key": "cal-bad", "gate": "preserves", "expected": false}
]
```

Each run must use the proposed evaluator and the same registered command,
interpreter, and declared dependencies as the revision. Confirmation input
bytes cannot be consumed for calibration. Labels still require independent
human or domain validation. After revision, collect fresh matched baseline and
candidate runs using the revised contract.

### Native test adapter

The included `scripts/experiment_native_check.py` can wrap one trusted native
test command. It requires a reviewed JSON configuration and case file:

```json
{
  "argv": ["/usr/bin/python3", "tests/test_product.py", "{{case_file}}"],
  "work_regex": "Ran (?P<count>\\d+) tests? in",
  "gate": "tests", "metric": "success",
  "timeout_seconds": 30, "max_output_bytes": 4096
}
```

Here the project test script must actually accept and use the supplied case
file and report a single matching test summary. Register the adapter as
`evaluator_file`, with the interpreter immediately followed by the adapter
path in `registry.argv`, then pass `--config`, its configuration path,
`--case-file`, and `{{case_file}}`. Include the config file and the
adapter's `json_contract.py` among `evaluator_dependencies`, along with
other trusted dependencies. The controller requires exactly one `--config`
argument and rejects the native adapter unless that configuration is frozen as
a declared evaluator dependency, along with its adjacent `json_contract.py`,
including during calibration and revision. For example, the relevant `init` fields are:

```json
{
  "target": "interaction",
  "trusted_interpreter": "/usr/bin/python3",
  "evaluator_file": "/path/to/skills/hill-climb/scripts/experiment_native_check.py",
  "evaluator_dependencies": [
    "/path/to/native-config.json",
    "/path/to/skills/hill-climb/scripts/json_contract.py"
  ],
  "registry": {
    "interaction": {
      "argv": ["/usr/bin/python3", "/path/to/skills/hill-climb/scripts/experiment_native_check.py", "--config", "/path/to/native-config.json", "--case-file", "{{case_file}}", "--case", "{{case}}"],
      "cwd": "."
    }
  }
}
```

The adapter executes argv without a shell, hashes
the case file, and reports a positive observed work count and test outcome.
It treats timeouts, unexpected exit codes, missing or ambiguous summaries, and
truncated output as errors. Review the command and regex: a matching summary
cannot by itself prove meaningful test coverage.

Hashes bind the files and receipts the controller sees. They do not authenticate
labels, prove evaluator independence, or establish that confirmation cases
remain hidden from a proposer. Without configured confirmation, the numeric result is provisional eligibility
for review. Confirmation assignments in the local controller are separate but
not sealed from host processes. The operator is responsible for protecting
their contents and reviewing the comparison's semantic evidence before delivery. Only the private integration ref advances; delivery follows the
repository's existing authorized integration process.

### Compose correctness with a quality judge

The native test adapter can also run a separate trusted quality judge. This is
useful when both revisions pass their tests and a quality metric must decide
between them. Add a `quality` object to the frozen native config:

```json
{
  "argv": ["/usr/bin/python3", "/trusted/quality_judge.py", "{{case_file}}"],
  "judge_file": "/trusted/quality_judge.py",
  "executable_sha256": "REPLACE_WITH_SHA256_OF_PYTHON",
  "judge_sha256": "REPLACE_WITH_SHA256_OF_JUDGE",
  "dependencies": [{"path": "/trusted/fixture.json", "sha256": "REPLACE_WITH_SHA256"}],
  "timeout_seconds": 30
}
```

The judge emits one JSON object with `case_sha256` and finite numeric `metrics`.
For a required qualitative criterion, provide `qualitative` with a numeric
`rating`, a rationale, and `evidence: ["self"]`, plus a nonempty `evidence`
object containing the observed material. The controller resolves `self` to
the retained, hashed evaluator receipt. The rating must match its metric.
The native test gate remains a mandatory gate when configured as such; a
higher quality score cannot compensate for failing it. List the judge and all
its dependencies in `evaluator_dependencies`, and pin interpreter and
installed packages separately. The runner rejects a judge or dependency inside
the exported candidate tree. These checks identify trusted code; they do not
make host execution a sandbox or prove the judgment is semantically correct.

### Bounded host-agent proposals

The invoking agent can inspect the task brief and frozen development evidence,
work on authorized arms, and submit changes through `freeze`. For a
small deterministic text proposal the `propose` action combines scoped edit,
receipt, and freeze. An `init` request may set `max_proposals` from 1 to 100;
the default is five. Proposal attempts are counted separately from trial starts
and remain counted after failed or uncertain attempts.

```json
{
  "action": "propose", "root": "/private/experiment", "arm": "candidate-a",
  "expected": {"commit": "FULL_ARM_COMMIT", "tree": "FULL_ARM_TREE"},
  "edits": [{"path": "src/changed-file.txt", "content": "revised content\n"}],
  "run_key": "proposal-a", "message": "Test one quality hypothesis",
  "writers_stopped": true
}
```

The native JSON action accepts only supplied text edits, not arbitrary provider
commands. Its local scripted provider makes no model call. The proposer
accepts no command-based agent provider; semantic proposals remain in the
invoking conversation. Do not interpret `max_tokens: 0` as proof of host spending.
A recorded proposal must still pass evaluation and any required confirmation.

### Parallel trials for one selected target

The `parallel` action accepts up to 128 predeclared assignments and a
`max_workers` value from 1 to 16. It atomically reserves every trial slot
before starting any worker. Each worker uses the selected local
executor and receives a separate frozen source export and the experiment's one registered target; a batch does not discover
or schedule other languages. Parallel timing may be affected by host resource
contention, so use sequential paired trials when isolation of a performance
measurement requires it.

```json
{
  "action": "parallel", "root": "/private/experiment", "batch": "round-1",
  "max_workers": 2,
  "trials": [
    {"side": "baseline", "case": "case-1", "rep": 0, "run_key": "base-1"},
    {"side": "candidate", "arm": "candidate-a", "case": "case-1", "rep": 0, "run_key": "candidate-1"}
  ]
}
```

`parallel-status` reads the retained batch manifest and ledger while workers
run. `parallel-recover` releases only reservations that were never dispatched;
dispatched or uncertain work and confirmation claims remain for reconciliation.
A `partial` response is not eligible evidence. The MAF workflow can sequence a
bounded parallel batch with other controller actions; its outer request list
is still sequential.

### Optional GEPA search over supplied text candidates

For an exploratory search over one scoped text artifact, install the pinned
optional engine in an isolated Python environment:

```sh
python3 -m venv /path/to/gepa-env
/path/to/gepa-env/bin/pip install --require-hashes -r skills/hill-climb/scripts/requirements-gepa.lock
/path/to/gepa-env/bin/python skills/hill-climb/scripts/experiment_gepa.py --request /private/gepa-request.json
```

The request names the existing experiment `root`, a unique `search`, one
`artifact_path` inside its editable scope, distinct declared `training_cases`
and `selection_cases`, supplied text `proposals`, `max_evaluations`,
`max_proposals`, `metric_range: [lower, upper]`, and `max_model_tokens: 0`.
It may include an `objective`. GEPA runs the existing evaluator on frozen Git
arms, records receipts, and consumes the same trial and proposal allowances as
the rest of the experiment. It independently caps evaluation calls because the
engine's internal bound is not the controller's budget authority.

This adapter searches supplied text; it does not invoke an agent or model.
Its suggestion is exploratory and cannot advance the champion without the
normal paired comparison, mandatory gates, and held-out confirmation. A GEPA
search has not been shown to outperform an evidence-guided host-agent proposal
at equal cost for a particular task family; measure that before adopting it as
an optimization default.
