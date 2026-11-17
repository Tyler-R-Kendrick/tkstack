# Design and evaluate nondeterministic behavior

1. Name the real task, observable outcome, constraints and failure modes. Use
   deterministic checks for state, schema, safety and other objective facts;
   use an LLM judge only for residual semantic judgment. Test the real system
   or its retained output, not a fabricated stand-in presented as production.
2. Reuse a project's existing evaluation suite when possible. Promptfoo is the
   default here: it is already used by TKStack, is open source, supports native
   `llm-rubric`, provider adapters, CI and OpenTelemetry traces. Inspect AI is
   an alternative when a task needs its agent and sandbox primitives. Preserve
   native framework formats; do not invent a parallel evaluation DSL.
3. Define a narrow rubric with success and failure anchors, required evidence,
   explicit judge provider/model/configuration and handling for ambiguity and
   errors. Include context the judge actually needs and treat model output and
   retrieved text as untrusted data. Calibrate on independently human-labeled
   good, bad, borderline and adversarial cases; inspect disagreements. Model
   consensus, a JSON schema, and temperature zero do not establish correctness.
4. Keep related examples together across train, selection and untouched
   confirmation splits; record provenance and avoid private data in public
   artifacts. Freeze the task, dataset, framework version, target, judge,
   rubric and runner before comparison. Repeated runs require actual independent
   trials and uncertainty estimates; do not use cache hits as new samples.
5. For agents, check the final environment and necessary safety/side-effect
   invariants; use traces to diagnose trajectories without enforcing an
   arbitrary exact path. Record model versions, calls, retries, latency, cost,
   errors, run counts and relevant tool state. OpenTelemetry/OTLP may carry
   traces when the real application emits them; a configured collector alone
   does not prove instrumentation or successful capture.
6. Set per-request and overall deadlines and an explicit spending limit before
   live execution. Retain elapsed monotonic time, timeout status and a bounded
   run receipt. A timeout does not prove remote cancellation or a product
   defect; reconcile uncertain side effects before retrying. A latency SLO or
   benchmark needs a realistic workload, baseline, repetitions and noise, not
   an arbitrary safety timeout.
7. Compare matched baseline and candidate runs with fixed gates; improve one
   hypothesis at a time. Confirm the fixed winner on genuinely untouched cases.
   Report inconclusive or exploratory results when no independent cases, real
   model calls or calibrated grader are available.

## Promptfoo workflow

Use the project's existing reviewed installation or the packaged npm lock
(`requirements/package.json` and `requirements/package-lock.json`, currently
Promptfoo 0.125.1). That version requires Node.js 22.22.0 or newer. To provision
the packaged lock without modifying an installed skill, copy the two manifests
to `/project/.tkstack/runtime/evalify/`, then run:

```sh
npm ci --prefix /project/.tkstack/runtime/evalify --ignore-scripts --no-audit --no-fund
```

Update the manifests together through npm and review the resulting lock.
Do not rely on `npx -y` to acquire unreviewed dependencies at execution time.
Use the framework's own YAML/JSON test formats, provider adapters and
`llm-rubric` assertions. Set the grader provider explicitly: otherwise framework
credential discovery can select a different model. Validate a known-good and a
known-bad answer and a grader-error case. A mocked provider demonstrates wiring,
not judge quality. `--no-share` prevents framework result sharing but target and
grader requests still reach their configured services.

The typed commands accept a project, existing configuration, explicitly supplied
Promptfoo executable, absent receipt path and (for run) an absent JSON output.
They enforce a default 20-second deadline (1–25 seconds), disable cache, sharing,
telemetry and update checks, and write a timing receipt. The outer TKStack runner
also has its own deadline. For longer workloads invoke the installed Promptfoo
CLI through an appropriate bounded supervisor; record equivalent timing and
cleanup evidence. See [execution](execution.md) for limits and side effects.
The receipt counts nonpassing results and the subset explicitly marked as
grader errors by Promptfoo. Inspect retained result details for other transport,
provider or grading errors; an unclassified failure is not proof of bad output.
The executable hash identifies only that file, not its dependency tree or a
remote model revision; retain the actual lock and provider configuration too.
On POSIX, direct helper execution isolates and cleans its process group; compiled
execution shares the enclosing runner's group. Detached descendants and remote
operations can outlive local cancellation and must be reconciled separately.

For example, after reviewing a project-owned config and installing the pinned
CLI, create the chosen output directory and invoke the mounted commands:

```sh
mkdir -p /project/.tkstack/eval-runs
.tkstack/tkstack --project /project skills learn -- evalify native validate \
  --project /project --config evals/my-suite.yaml \
  --executable /project/.tkstack/runtime/evalify/node_modules/.bin/promptfoo --receipt .tkstack/eval-runs/validate.json
.tkstack/tkstack --project /project skills learn -- evalify native run \
  --project /project --config evals/my-suite.yaml \
  --executable /project/.tkstack/runtime/evalify/node_modules/.bin/promptfoo --output .tkstack/eval-runs/result.json \
  --receipt .tkstack/eval-runs/run.json
```

Each output and receipt must be absent before invocation. The command does not
create a dataset, install a framework, or authorize provider spending by itself.
It reserves both paths exclusively before starting Promptfoo, so overlapping
runs cannot silently share either name. An interrupted or crashed process may
leave an empty reservation; inspect provider-side effects and the retained files
before removing it or retrying.

Sources: [Promptfoo model-graded rubrics](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/),
[Promptfoo OTLP tracing](https://www.promptfoo.dev/docs/tracing/),
[Inspect model grading](https://inspect.aisi.org.uk/model-graded.html), and
[Anthropic agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
