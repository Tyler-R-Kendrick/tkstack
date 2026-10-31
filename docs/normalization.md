# Owned skill normalization

All 19 packages under `skills/` share the owned Skillify/Codify command protocol:
reserved default help and version, an explicit contract `model`, a retained-report
`verify`, and a current compiled `scripts/workflow.lock.json`. Existing native
helpers remain the owners of their actual algorithms. Their typed native
bindings call that code; the shared runtime does not reimplement their policy.
Pinned `vendor/` packages remain unchanged.

```sh
.tkstack/tkstack skills write -- help
.tkstack/tkstack skills write -- model
.tkstack/tkstack skills write -- verify --report /repo/.tkstack/evidence/write-report.json
.tkstack/tkstack skills codify -- native compile --help
.tkstack/tkstack skills learn -- native capture --help
python3 scripts/tool.py command-schema -B scripts/check_skills.py
```

`model` describes required facts, criteria, and actual automation limits using
JSON Schema. It is a contract model, not an implicit LLM/provider selection.
`verify` validates recorded facts, criterion coverage, and hashes of actual
retained evidence files. It explicitly reports semantic inspection as
`recorded-not-authenticated`. It cannot authenticate review, authority, remote
state, or quality. Domain-native gates remain required. Running compiled code
uses the shared runner's ignored temporary materialization; it does not change
application/learning records. Reserved help/version and direct checks create no
state. Relative external paths resolve against the selected workspace.

## Coverage of every owned skill

Every row has a modified progressive command index, an explicit model, compiled
code, actual positive/transfer/adversarial proof tests, and a completed real
SkillOpt decision trial. The native/semantic column states what those mechanical
checks do not replace.

| Skill | Executable core / native binding | Required domain work |
| --- | --- | --- |
| codify | Model/report gates; native scaffold, check, compile, run | One-time semantic lowering and actual native outcome verification |
| document | Source/knowledge ownership and evidence constraints | Grounded composition, link/command checks; actual OpenWiki lifecycle if selected |
| fal-ai | Provider/job/output claim constraints | Selected provider submission/recovery and actual retrieved media inspection |
| flowify | Model/report gates; native scaffold, inspect, check | Real MAF/Rhai runtime validation and execution |
| headroom | Reversibility, fidelity, routing constraints | Actual compressor/proxy and exact original-context retrieval |
| hill-climb | Model/report gates; native paired receipt comparison | Real comparable measurements, noise, keep/revert and untouched confirmation |
| hookify | Model/report gates; native policy check, replay, registration emission | Actual native-host activation and tool-boundary enforcement |
| instructify | Model/report gates; native hashed plan, check, apply | Instruction meaning and observed harness loading |
| investigate | Sources, falsification and scope constraints | Actual source tracing, reproduction and uncertainty resolution |
| learn | Model/report gates; native capture, rule, experience, show, session review | Actual user provenance, scoped abstraction and useful promotion |
| lintify | Model/report gates; native backend scaffolding | Real native CLI discovery, diagnostics, bad/good/transfer/exception cases |
| open-design | Render/accessibility/provider claim constraints | Actual rendering, visual review and selected application/provider |
| reusify | Model/report gates; native catalog check/find and source assessment | Semantic equivalence and native template/generator/consumer checks |
| rtk | Command, permission, unfiltered-evidence and billing claim constraints | Actual RTK executable, command filtering and observed savings |
| sdlc | Model/report gates; retained durable SQLite task coordinator | Full BDD/contracts, sparse COW worktrees, independent evidence review and authorized delivery |
| skillify | Model/report gates; native check, scaffold, convert, normalize, compile | Actual procedure design, implementation, tool outcomes and referenced semantic work |
| tkstack-principles | Least-inference and bounded-ownership constraints | Actual sufficiency reasoning and evidence of the selected mechanism |
| unslop | Model/report gates; native catalog, grade and check | Actual artifact inspection, scoped judgments and legitimate exceptions |
| write | Source fidelity, author meaning and publication constraints | Actual composition and reading of the complete requested draft |

This is executable coordination and verification coverage. It does not claim
that deterministic code can produce or judge arbitrary prose, images, interfaces,
or novel decisions. No provider/model/account is silently selected or changed.
Headroom/RTK/media need their real runtimes; OpenDesign's application/daemon and
Stitch authentication retain their separately reported requirements.

## Use our own authoring mechanisms

The normalization followed Learn's evidence-backed improvement procedure,
Skillify's progressive packaging/normalizer, Codify's real compiler/runner, and
Reusify's shared-code rule. Three equivalent strict JSON readers were extracted
into canonical `skills/codify/scripts/json_contract.py`; compiler, command and
contract runtimes reuse it. One canonical `package_runtime.py` supplies packaged
copies for all 19 standalone skill cores. Generated copies are distribution
outputs, not independent implementations or evidence for further extraction.

`skillify normalize` reads an explicit authored contract/profile and generates
typed command definitions, common runtime files, execution references, and a
relative source-generation manifest. It preserves native helper code, detects
modified generated files before overwriting/removing them, and supports a
read-only dry-run. Cooperative package writers use an OS lock; publication is
atomic per file. An interrupted source update still requires a fresh successful
compile before delivery. Runtime/session records stay in `.tkstack`; the relative
generation manifest and lock are authored package/build artifacts.

```sh
python3 scripts/tool.py skillify normalize skills/write \
  --profile skills/write/scripts/contract.json --dry-run
python3 scripts/tool.py skillify normalize skills/write \
  --profile skills/write/scripts/contract.json
```

For a real change, inspect the profile and existing assets first. Update actual
native bindings/criteria and meaningful cases, normalize, review the generated
diff, update the index/version/marketplace and focused docs, and compile actual
code. Include the package's templates/resources when native helpers need them:

```sh
python3 scripts/tool.py codify compile skills/write/SKILL.md \
  --entrypoint skills/write/scripts/run.py \
  --cases skills/write/scripts/workflow.cases.json \
  --root skills/write --include skills/write \
  --output skills/write/scripts/workflow.lock.json --project .
```

Compilation cases establish model/dispatch smoke behavior. The behavioral suite
additionally invokes every skill's compiled verifier with real retained files,
transfer inputs, modified hashes, omitted criteria, and contradictory domain
claims; it exercises the native authoring, learning, policy replay, instruction
planning, workflow inspection, and measurement adapters. Synthetic proof fixtures
are labeled as such and do not impersonate production provider evidence.

## What the improvement trials showed

[Recorded current-source results](../evals/results/2026-10-31-owned-skills.json)
cover all 19 current `SKILL.md` hashes and 59 reviewed author-created
train/validation/test scenarios. The pinned SkillOpt-Sleep handoff used 65 actual
fresh-context evaluator calls, including final-source reruns of the two compiler
skills. Each evaluator received only its exact pending prompt; no inline or mock
answer was substituted. Private full prompts/replies and provenance remain in
ignored local evidence.

All policy decisions passed. Every held-out gate saw `1.0 → 1.0`, correctly
rejected the tie, and proposed/adopted no extra instruction edit. The engineering
normalization changed every package independently of that outcome. This is an
attempted measured policy improvement with no measured semantic gain, not a
general quality claim. Reused fixed scenarios, narrow action-choice tasks, and
relay/cache usage estimates are explicit limits. Broader native/creative outcomes
need their real task adapters and inspected artifacts.

## Keep the pattern consistent

`scripts/check_skills.py` reuses Skillify validation and Codify freshness checks,
checks all owned marketplace entries, shared runtime/state copies, required
typed commands, contract schemas, and reviewed decision splits. Doctor runs it
through the managed command interpreter when ready, and explicitly reports pending
verification if an offline first setup lacks it. The repository's
[CI workflow](../.github/workflows/skills.yml) also checks conformance, docs, and
the full offline regression suite without running a paid model or provider job.
Native Graphify and AI SDK integration checks require their explicitly enabled
local runtimes; those additional checks are covered by the retained local run.

Frozen source modes use Git-portable executable status, so secure checkout
umasks do not invalidate identical code while changed executable status still
does. Authored text uses LF attributes; pinned vendor bytes are excluded from
normalization. A real commit/clone regression verifies cached artifact portability.
Existing source/case/code drift still requires explicit recompilation.

Self-project installation retains portable repository-owned instruction pointers
in `AGENTS.md` and `CLAUDE.md`; external installations preserve checkout-specific
ownership. Fresh self-install, relocation and foreign-ownership regressions cover
this boundary in addition to the compiled-package clone check.

Native compiler bindings retain explicit provider/model/harness configuration, selected project and deadline. Nested executions share owned process groups and terminate remaining group processes when their invocation finishes or fails. Native scratch uses the shared scoped `.tkstack/sessions/` primitive.
