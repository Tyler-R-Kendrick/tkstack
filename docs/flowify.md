# Executable workflow authoring

Use `/flowify <procedure>` or `$flowify` to create a reusable executable workflow.
The canonical package is [`skills/flowify`](../skills/flowify/SKILL.md), installed
in Codex, Claude Code, and Cursor and listed in the root marketplace.

Flowify defaults to Microsoft Agent Framework declarative YAML for tool/code
workflows. Its other supplied backend is **Rhai**, the Rust scripting library
used by Grok's `xai-workflow` crate. It can retain another existing suitable
project engine instead of forcing a translation. Definitions use the actual
DSLs, not a new tkstack workflow schema.

The output is a native definition plus its executable host/bindings, inputs,
dependencies/lock, invocation, and meaningful cases. Conditions, dependency
readiness, and outcome gates use code first. Independent work uses bounded
concurrency, owned state and stable fan-in. Register an agent only for residual
judgment; don't introduce agent calls merely to parallelize ordinary code.

```sh
python3 skills/flowify/scripts/flowify.py scaffold \
  --backend maf --target /repo/workflows/check-contracts --name check-contracts
python3 skills/flowify/scripts/flowify.py inspect \
  --backend maf --file /repo/workflows/check-contracts/workflow.yaml
```

The MAF starter has a real `InvokeFunctionTool` YAML action, a Python host, and
a deterministic file-hashing binding. The binding streams input files, bounds
parallel reads, preserves input order, rejects missing/escaping/duplicate paths,
and joins work before reporting failure/cancellation. Its host verifies that
the graph emitted the actual successful binding receipt. The example is not
the user's finished requested procedure; replace its stages with the actual
workload and test those public outcomes.

The Rhai starter performs a model-free Grok-host fingerprint operation. Its host
fingerprint is not the raw text SHA-256. A generic Rhai binary does not supply
Grok's host functions, journal, cancellation, or agent budget controls.

## Native setup and validation

The generated MAF package pins the published `agent-framework-declarative==1.4.0`
and includes a hash-locked dependency set for the tested CPython 3.12/Linux
profile. Its Power Fx expressions need a supported .NET runtime; installing the
Python packages alone does not satisfy that dependency. Regenerate/test a lock
for another platform rather than claiming the example lock is universal.

Within an appropriately provisioned project environment:

```sh
python /path/to/flowify/scripts/flowify.py check \
  --backend maf --file /repo/workflows/check-contracts/workflow.yaml
python /repo/workflows/check-contracts/run.py \
  --project /repo --input /repo/workflows/check-contracts/inputs.json --jobs 4
```

For Grok/Rhai, use the actual host or explicit native source checkout:

```sh
python3 skills/flowify/scripts/flowify.py check \
  --backend rhai --file /repo/workflows/procedure/workflow.rhai \
  --grok-source /path/to/grok-build
```

The Rust command is offline/locked and requires cached dependencies. Its
upstream validator uses stub inputs/host responses; it is not a real-agent or
production-effect run. Source inspection does not compile Rhai. Missing native
runtime returns exit 3, never a validation pass.

MAF graph construction similarly does not prove binding/effect execution.
Tool errors can be stored as error values, so the workflow/host must reject
failed outcomes explicitly. YAML action lists are sequential, and the native
graph uses superstep barriers. Use supported builders/executors or bounded async
bindings rather than inventing a `Parallel` YAML action. See
[backend contracts](../skills/flowify/references/backends.md),
[validation levels](../skills/flowify/references/validation.md), and
[exact primary sources](../skills/flowify/references/sources.md).

## Verification performed here

The checked-out Microsoft source advertises 1.4.1, while PyPI's published release
is 1.4.0. The generated pin was verified against PyPI rather than assumed from
source metadata. Native checks ran in an isolated ignored environment under
`.tkstack/evidence/flowify/maf-venv`, with a project-local .NET **8.0.33** runtime
whose SHA-512 matched Microsoft's release metadata. Global Python/home
configuration was left alone.

Actual MAF 1.4.0 graph construction and execution passed:

- A two-file case emitted the known SHA-256 values for `abc` and empty bytes.
- A distinct one-file case emitted the expected single result.
- A missing-file case exited with failure and no success receipt.

Native JSON, stderr, source/input identities, and the .NET receipt are retained
under `.tkstack/evidence/flowify/`. The runtime prerequisites remain local to
that validation environment; choose its interpreter and set `DOTNET_ROOT` when
reusing it, or provision the generated workflow's own environment.

Unit checks separately verify typed inputs, known hash vectors, bounded overlap,
stable result order, cancellation cleanup, failure propagation, malformed YAML,
source/validation separation, collision protection and standalone scaffolding.
They need local IPC for asyncio thread wakeups; a network-restricted sandbox
may deny that local socket operation. No external service is used by those
binding tests. Rust/Cargo/Grok are unavailable here, so native Rhai compilation
and production host execution have not been claimed.

## Other authoring tools

`skillify` teaches when/how to use the procedure. `flowify` creates its executable
state/data flow. `instructify` provides standing guidance and short invocation
pointers. `hookify` can invoke an authorized deterministic gate on an event.
`learn` retains real correction/experience evidence. Existing SDLC and skill
evolution requirements still apply when those workflows are active. Installing
this skill does not register or start a production workflow.
