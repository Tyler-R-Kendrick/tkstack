# Compile the procedure into a tool

The skill is an intermediary authoring artifact and code-mode prompt. The
production executable is a workflow definition under `scripts/`: explicit
inputs, deterministic control/data flow, real tool/API calls, validated outputs,
and defined failures. Markdown teaches discovery and invocation rather than
making the agent reconstruct that algorithm every time.

## Create or convert

1. Resolve the requested scope and canonical owned skill. Read its actual
   procedure and relevant artifacts; inspect existing helpers and reusable code.
   Keep audit/preview read-only and source snapshots immutable.
2. Define the callable contract first: inputs, defaults, outputs/artifacts,
   errors, effects, and completion. Decompose operations by real dependencies
   and read/write ownership. Turn facts, branching, gates, and algorithms into
   code. Freeze authoritative constraints outside model-generated content.
3. Choose the smallest actual runtime. A pure Python function/CLI is sufficient
   for a simple deterministic procedure. Use TypeScript and Vercel AI SDK for
   explicit inference boundaries. Retain an existing suitable native engine;
   `flowify`, when available, supplies MAF YAML or Grok-hosted Rhai. Keep those
   definitions and bindings in `scripts/` and invoke their actual host. The AI
   SDK supplies inference/harness interfaces; it is not a durable workflow
   engine, nor a substitute for MAF/Rhai validation.
4. Create the executable definition and thin CLI/tool wrapper. Reuse existing
   functions and native engines. Compile decisions, retries, limits, dependency
   readiness, fan-in, and failure propagation into code; do not invent a private
   workflow DSL or leave required steps in an agent's checklist.
5. Implement the actual procedure. If a residual judgment needs inference,
   isolate it behind a named [profile](inference.md), send only relevant state,
   validate its output, and apply the same deterministic policy gate. A decision
   model may remain probabilistic; an LLM behind an API stays an LLM. Missing
   profiles or invalid/unknown output must not become success or trigger an
   unrequested provider fallback.
6. Update `SKILL.md` to index the callable entrypoint and topic/feature/command/
   parameter references. Document exact setup, CLI/import/tool registration,
   schemas/examples, errors, effects, and how to inspect output. Keep the initial
   Markdown as provenance or design input; do not maintain a second competing
   executable algorithm in prose.
7. Run the workflow with original, transfer, and negative/boundary cases. Check
   actual output and caller behavior. Repeated pure inputs must produce the same
   output; replay external observations explicitly. Test bounded concurrency,
   cancellation, partial failure, and owned writes where applicable. Native
   execution evidence is required before calling the tool production-verified.

The packaging helper's `scaffold` and `convert` seed **drafts**. They do not
transpile arbitrary natural language or infer a correct algorithm automatically.
The authoring agent completes steps 2–7 before delivering the requested skill.
Neither a successful scaffold nor a Markdown-only migration fulfills conversion.
No-op or prompt-forwarding scripts do not fulfill deterministic execution.

## Package layout and interfaces

```text
skills/example/
  SKILL.md                 # code-mode prompt, invocation/discovery index
  LICENSE
  scripts/
    workflow.py or .ts      # executable procedure/source of truth
    run.py or .ts           # JSON CLI wrapper
    tool.ts                 # AI SDK tool export for the TS backend
    ...                     # native definitions, schemas, bindings, locks
  references/
    tool.md                 # setup, tool I/O, subcommands/parameters, errors
    inputs.md
    procedure.md            # design/semantics; not a competing runtime
    verification.md
```

The generated Python CLI accepts `--input <json-file|->`; TS accepts
`--input <json-file>` and optional `--config <profiles-json>`. Run from any
directory by supplying the actual script/input paths. The tool guide's examples
run from the skill directory. Standard output is the JSON result; diagnostics
go to stderr. Success exits 0, failure 1, unfinished workflow 3; Python argparse
usage errors exit 2. A generated TS `createWorkflowTool(inference)` exports a
native AI SDK `tool()` with input/output schemas for programmatic registration.

Pure-code workflows need no model credentials. The optional AI SDK runtime
starts with empty profiles. Configure actual model/provider/harness definitions
only when a workflow explicitly calls them. Creating/scaffolding a package does
not start a model, agent, sandbox, publication, or a standing hook.

`convert` retains the exact prior `SKILL.md` bytes as
`references/source-skill.txt`, creates new execution assets, and replaces the
body with an invocation index while preserving frontmatter and license. It
rejects path/file collisions instead of overwriting existing helpers or guides.
For an existing executable skill, adapt/reuse that code directly and update its
tool interface rather than force a second scaffold. Cooperative conversions use
one writer lock, exclusive publication, stale-source checks, and rollback on
ordinary errors. Crashes and nonparticipating writers are not a global transaction.

## Compile the verified artifact

Codify now owns the reusable code-generation templates, inference runtime,
compiler, and locked runner. Skillify packages the skill-specific interface and
ships a generated standalone copy. After implementing and verifying the actual
procedure, run `skillify.py compile <skill> --cases <contract-cases.json>`.
This freezes code/provenance under `scripts/workflow.lock.json`; document its
locked invocation in the tool index. The runtime executes those frozen bytes,
checks stale inputs, and never reinterprets Markdown or rebuilds implicitly.
See [commands](commands.md#compile-a-completed-skill). Pure-code runs require no
model; residual inference stays declared and explicitly configured. Native
MAF/Rhai definitions can be frozen through their actual host bindings.

## Completion check

Run `skillify.py check <skill> --require-tool`, plus the real native type/graph
and execution checks. `--entrypoint scripts/<existing-tool>` supports a different
owned entrypoint. The checker establishes packaging, path containment, and the
absence of the starter's known unimplemented workflow; it cannot establish
semantic equivalence, trigger quality, inference reduction, or correct effects.
Do not mark a scaffold complete by merely deleting a placeholder marker.

State the executable paths, invocation, observed cases/results, remaining
probabilistic decisions, and native evidence gaps. Keep original requested
effects and read-only boundaries intact while replacing repeated interpretation
with an executable artifact.
