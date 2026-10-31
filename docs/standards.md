# Agent standards

These are the initial tkstack defaults, informed by Pstack, Tstack, and Matt
Pocock's skills. Task instructions and the active project's rules take precedence.

## Personal principles

Apply [tkstack principles](../skills/tkstack-principles/SKILL.md) and the
applicable full references when designing or reviewing any code, skill, hook,
rule, workflow, or harness configuration:

- **Deterministic first:** implement facts, policy, routing, state transitions,
  and objective gates in code. Use constrained decision models/APIs for residual
  ambiguity, then LLMs/agents only when the earlier mechanisms are insufficient.
  A generative endpoint remains the last tier even when called through an API.
- **Concurrency by design:** make independent work safely parallel with explicit
  dependencies, isolated mutable state, bounded capacity, and stable fan-in.
  Serialize the smallest region required by a real dependency, ordered effect,
  canonical writer, resource limit, or measurement constraint.

These principles guide all installed workflows through the native instruction
pointers. They complement Pstack; the vendored principles remain unchanged.
See [installation, examples, and boundaries](principles.md).

## Routing

- A full `sdlc` implementation request selects the development lifecycle: frozen
  workloads, atomic concurrent task graphs, BDD and real consumer/provider
  contract tests, independent evidence review, and babysat stacked PRs with
  root-first squash merges. Apply that workflow's test and delivery strategy
  across the other engineering skills. Scoped plan/design/verify/review/delivery/
  handoff requests select only that branch. See [the SDLC guide](sdlc.md).
- Prefer owned portable procedures and conditional references. Use `investigate`
  for system tracing, rationale, primary-source research, and diagnosis; `write`
  for human-facing composition; `document` for source-grounded knowledge and
  handoffs. SDLC references cover requirements, interfaces, testing, review, and
  delivery. Native source workflows remain available for explicit use. See
  [the source decisions](skill-distillation.md).
- Use Matt's `ask-matt` to choose between requirements, specs, tickets,
  implementation, and domain modeling. Within Matt's workflows, use `matt-tdd`;
  the installer rewrites their TDD calls to that name.
- Use Tstack for PR lifecycle work: `file-pr`, `babysit-pr`, `takeover`, and
  `modernize`. `full-stop` is the workflow for preparing a PR for human merge.
  Invoke `full-send` when the user explicitly requests its autonomous merge flow.
- Use personal `unslop` when grading AI outputs across writing, code, tests,
  websites, and media. Record user-identified patterns in the shared ledger;
  apply matching confirmed criteria with legitimate exceptions. Its `grade`
  mode is read-only. Pstack's prose-only rules remain `pstack-unslop`; `deslop`
  can assist with code cleanup. See [anti-slop review](unslop.md).
- Use `hill-climb` for explicitly requested sustained optimization. Prove and
  freeze a sensitive evaluation, measure noise, keep or revert one hypothesis,
  and confirm the winner on untouched cases. Quality and meaningful behavior
  remain gates when optimizing cost or speed. See [the workflow](hill-climb.md).
- Use `learn` when the user corrects reasoning or expresses frustration. Capture
  the exact evidence and apply a scoped reasoning rule from the shared steering
  store. See `docs/learning.md`.
- Use `codify` for prompt/Markdown compilation and reusable executable lock
  artifacts. Resolve meaning once into native code, verify its real contracts,
  and execute the frozen code on subsequent runs. Reject stale inputs and
  rebuild explicitly. Skillify consumes this engine for skill packaging;
  Flowify retains native DSL/host design. See [compilation](codify.md).
- Use `skillify` for an explicit request to capture a reusable procedure,
  adapt a source skill, or update an owned package. Treat `SKILL.md` as its
  table of contents and intermediary code-mode prompt, linking tool invocation
  and topic/feature/subcommand/parameter contracts in `references/`. Compile the
  actual workflow into `scripts/`; invoke that executable instead of repeatedly
  interpreting prose. Prefer the locked Vercel AI SDK boundary for explicit model,
  native Decisions, and harness profiles. See [tool conversion](skillify.md).
  Use `hookify` to encode an
  explicit rule as a deterministic hook/check; prefer types, lints, contracts,
  or CI when they establish the invariant more directly. Existing `learn`
  provenance and SkillOpt gates still apply to their respective scopes. See
  [authoring and enforcement](authoring.md).
- Use `lintify` for native CLI lint-rule authoring. Prefer an existing rule,
  then deterministic code/AST/query enforcement. Markdown intent may compile
  to a deterministic check; semantic prompt checking remains a model fallback
  with explicit runtime, scope, budget, and false-positive/unknown behavior.
  Validate real CLI discovery, fixtures, diagnostics, and exits. See
  [lint authoring](lintify.md). `hookify` owns event interception and may call
  an existing lint command when that integration is requested.
- Before reproducing a code pattern, look for suitable existing code and reuse
  assets, including the project's catalog when present. Use `reusify` for three
  verified occurrences or an upcoming third use. Choose a template, snippet,
  native generator, module/library, or component by its actual update/ownership
  semantics. Migrate in-scope uses and register the canonical interface so future
  agents invoke it instead of inferring the same implementation. See
  [the reuse workflow](reusify.md). Source counts alone do not prove equivalence.
- Use `flowify` for a reusable executable workflow. Author an existing suitable
  DSL with explicit inputs, dependencies, code/tool bindings, failure gates,
  bounded concurrency, and execution evidence. MAF YAML is the default here;
  Grok uses Rhai with additional host functions. A static parse or mock-host
  result is not production execution. See [workflow authoring](flowify.md).
- Use `instructify` for stable agent context and scoped working expectations.
  Keep procedures in `skillify`, mechanical enforcement in code/`hookify`, and
  correction history in `learn`. Inspect inherited guidance/imports and update
  the canonical source without silently broadening scope or replacing foreign
  sections. See [instruction authoring](authoring.md#instructify).
- Use `lever` for measurement-first loop cards, experiment arms, briefs, and
  explicitly requested delivery operations. Resolve its repository/personal
  dials and current task authorization. When combined with `sdlc`, keep its
  BDD/contract, isolation, and evidence requirements. Link structural correction
  fixes back to `learn` evidence rather than creating a second raw-feedback
  ledger. SkillOpt remains the selected custom-skill revision gate. See
  [Lever setup](lever.md).
- Use Impeccable for interface design, Ponytail for reuse and subtraction, and
  `design-md` for the requested Stitch design-system workflow. Honor an explicit
  media provider choice between fal.ai and Higgsfield.

## Engineering

Define interfaces and data shapes before building across a boundary. Prefer
small public interfaces, explicit ownership, and removing unnecessary machinery.
Fix root causes. Prove behavior at meaningful public seams with a reproduction,
focused test, runtime observation, or another direct check appropriate to the
change. Keep work in small units that can be verified independently.

Use top-level TypeScript imports and exhaustive switches for discriminated
unions. The corresponding Cursor Team Kit rules are installed for Cursor.

## Harnesses and delegation

Use the active harness's capabilities and available models. Preserve the
provider requirements of a requested multi-model workflow. If it requires a
model or tool that is unavailable, state the limitation and the evidence you
can provide. Do not represent a single-model review as a completed council.

Installed skills are available tools; their presence does not invoke them or
authorize their downstream effects. Use delegation when the task and governing
instructions authorize it. Keep credentials and machine-specific state outside
the repository.

## Keeping the setup reproducible

Keep upstream snapshots unchanged. Pin revisions, file contents, symlink
targets, and executable modes in `sources.lock.json`. Keep name adaptations in
`harnesses/skills.json`; generated views belong in `.tkstack/`. Put new personal
skills, agent definitions, and harness settings alongside the upstream sources,
not inside them.
