# Host-bound evaluation

The current agent and the harness that invoked it remain responsible for the
task and semantic judgments. Do not launch another agent, select a model or
provider, or start a second agent harness to produce an evaluation. The host
may provide a trustworthy model identity, deadline, duration or trace; record
what it actually exposes and mark unavailable values unknown.

1. Define the actual task, observable outcome, constraints and concrete
   failure modes. Check objective state, schemas, safety and tool effects
   deterministically. The invoking agent judges only the residual semantic
   question in the current conversation.
2. Establish a narrow rubric with good, bad, borderline and adversarial
   examples. When available, use independently human-reviewed reference
   labels and inspect disagreements. A matching output or schema alone does
   not establish that a semantic judgment is reliable.
3. Keep related cases together across development, selection and confirmation.
   A case or label the current agent has seen is not a blind holdout. If the
   host cannot supply unseen cases without starting a different agent or model,
   report the confirmation as unavailable; do not manufacture independence.
4. Retain actual outcomes, rubric, supplied labels, model/host identity when
   exposed, elapsed time and timeout outcomes. Avoid putting private prompts in
   public reports. An agent's reported success is not proof that the target
   environment reached the requested state.
5. Set bounded operation and overall deadlines, and retain their observed
   elapsed times. A timeout is a safety ceiling, not a latency SLO, and does not
   prove remote cancellation. A performance claim needs representative work,
   repeated measurements, uncertainty and appropriate guardrails.
6. Improve one hypothesis at a time using matched evidence. Repeated
   same-context judgments are observations, not independent samples. Report
   limitations and failures rather than presenting an authored fixture or a
   framework pass as a measured model-quality gain.

## Offline framework scoring

Promptfoo 0.125.1 is pinned in the package lock and is used as an established
assertion library, not as an agent harness or model provider. The helper invokes
only its fixed `equals` assertion on judgments already supplied by the invoking
agent; it accepts no framework config, custom executable, provider or model.
It disables telemetry and update checks and blocks common Node network APIs.
It does not execute a target or make an LLM-as-a-judge call: the current agent
does the semantic judging as part of its existing conversation.

If needed, install the integrity-locked dependency into the selected project:

```sh
mkdir -p /project/.tkstack/runtime/evalify
cp <evalify>/requirements/package*.json /project/.tkstack/runtime/evalify/
npm ci --prefix /project/.tkstack/runtime/evalify --ignore-scripts --no-audit --no-fund
```

The runtime needs Node.js 22.22.0 or newer. Update the manifests together and
review the lock. A project-owned input must be at most 1 MiB and contain:

```json
{"version":1,"source":"invoking-agent","cases":[
  {"id":"known-good","judgment":true,"reference":true,"elapsed_ms":120},
  {"id":"known-bad","judgment":false,"reference":false,"elapsed_ms":null},
  {"id":"current","judgment":true,"reference":null,"elapsed_ms":null}
]}
```

`reference` is a reviewed expected judgment for calibration, or null for a
current case. `elapsed_ms` is a real host-observed duration, or null when not
available; never invent it. The output counts matching labeled judgments,
separates false positives from false negatives, and counts current pass judgments.
Its timing summary reports the number of observed and missing durations and the
median and maximum of observed values; absent observations remain unknown.
It is a descriptive summary, not proof of calibration,
host identity, an independent evaluator, or model performance.

```sh
.tkstack/tkstack --project /project skills learn -- evalify native validate \
  --project /project --cases evals/host-judgments.json --receipt .tkstack/eval-runs/validate.json
.tkstack/tkstack --project /project skills learn -- evalify native run \
  --project /project --cases evals/host-judgments.json --output .tkstack/eval-runs/results.json \
  --receipt .tkstack/eval-runs/timing.json
```

Create the output directory first. Output and receipt paths must be absent;
the helper reserves them before analysis. Its 20-second default deadline
(1–25 seconds) and timing receipt cover offline processing only, not the
agent's prior judgment. A crash can leave an incomplete reservation. Direct
POSIX execution cleans the ordinary process group; detached descendants and
remote actions require separate reconciliation.

Sources: [Promptfoo assertion API](https://www.promptfoo.dev/docs/configuration/expected-outputs/),
[Anthropic's agent evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents),
and [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/).
